# encoding=utf8
# Copyright (c) 2022 Circue Authors. All Rights Reserved

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from distutils.command.build import build
from tabnanny import verbose
from sklearn.base import BaseEstimator, TransformerMixin, RegressorMixin, clone
import sys
import os
import json
import warnings
import joblib
import argparse
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.linear_model import Lasso, Ridge
from sklearn.linear_model import ElasticNet, LinearRegression, LogisticRegression
from sklearn.kernel_ridge import KernelRidge
from sklearn.ensemble import AdaBoostRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
import random
import tensorflow as tf
from tensorflow.keras.wrappers.scikit_learn import KerasRegressor
import xgboost
from xgboost import XGBRegressor

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.getcwd()))
from dataset.dataset import Dataset
from tools.averaging_model import *
warnings.filterwarnings('ignore')

__MODEL__AVALIABLE__ = {
    "ElasticNet": ElasticNet,
    "Lasso": Lasso,
    "Ridge": Ridge,
    "KernelRidge": KernelRidge,
    "AdaBoostRegressor": AdaBoostRegressor,
    "GradientBoostingRegressor": GradientBoostingRegressor,
    "SVR": SVR,
    "LinearRegression": LinearRegression,
    "XGBRegressor": XGBRegressor,
    "SVR": SVR,
}


class Train:
    """
    训练类
    """

    def __init__(self, args):
        """
        初始化
        :param args: 初始化信息
        """
        self.args = args
        self.model = None

    def manual_seed(self, seed_value):
        os.environ['PYTHONHASHSEED']=str(seed_value)
        random.seed(seed_value)
        np.random.seed(seed_value)
        tf.random.set_seed(seed_value)

    def regression(self, datasets, model_cfg=None, save_model=False):
        """
        回归函数
        :param datasets: 数据集
        :param alpha_train: 惩罚项系数
        :param l1_ratio: L1模型权重
        :param regression_type: 回归模型类型
        :param log_target: 是否进行log变换
        :param model: 使用模型
        """
        # get three sets
        self.manual_seed(4)
        x_train, y_train = datasets.get("train")
        y_scaler = Dataset.get_label_scaler(y_train)

        n_models = len(model_cfg)
        model_selects = []
        for i in range(n_models):
            model_name = model_cfg[i]["model_name"]
            if model_name == "KerasRegressor":
                model_selects.append(
                    OptionalNnModels(
                        KerasRegressor(build_fn=build_nn, 
                                       epochs=model_cfg[i]["epochs"], 
                                       batch_size=model_cfg[i]["batch_size"],
                                       verbose=0),
                        target_scaler=y_scaler))
            else:
                model = __MODEL__AVALIABLE__.get(model_name, None)
                if model is None:
                    raise ValueError("model_name is not available")
                model_selects.append(
                    OptionalModel(
                        model(**model_cfg[i][model_name]),
                        log_target = model_cfg[i]["log_target"]
                    )
                )


        # regr = AveragingModels([
        #     OptionalModel(
        #         SVR(kernel="poly", degree=3, coef0=3, C=0.02), 
        #         log_target=True),
        #     OptionalModel(
        #         ElasticNet(random_state=4, alpha=0.005, l1_ratio=0.9),
        #         log_target=False),
        #     OptionalModel(
        #         KernelRidge(kernel="polynomial", degree=5, coef0=3, alpha=0.88),
        #         log_target=True),
        #     OptionalModel(
        #         XGBRegressor(booster='gbtree',colsample_bytree=0.8, gamma=0.1, 
        #                         learning_rate=0.02, max_depth=3, 
        #                         n_estimators=276,min_child_weight=0.8,
        #                         reg_alpha=0, reg_lambda=1,
        #                         subsample=0.8, random_state =4, nthread = 2),
        #         log_target=False),
        #     OptionalModel(
        #         GradientBoostingRegressor(n_estimators=64, max_depth=5, min_samples_split=3, random_state=4),
        #         log_target=True),
        #     OptionalNnModels(
        #         KerasRegressor(build_fn=build_nn, epochs=700, batch_size=16, verbose=0),
        #         target_scaler=y_scaler)
        # ])
        regr = AveragingModels(model_selects)

        # fit regression model
        regr.fit(x_train, y_train)
        # predict values/cycle life for all three sets
        pred_train = regr.predict(x_train)

        # mean percentage error (same as paper)
        error_train = mean_absolute_percentage_error(y_train, pred_train) * 100
        if save_model:
            # joblib.dump(regr, f"./model/model_regression.pkl")
            regr.save("./model/model_merge")
        else:
            self.model = regr
        print(f"Regression Error (Train): {error_train}%")

    def run_regression(self):
        """
        训练回归模型主参数
        """
        model_cfg = self.args.model_cfg
        features = Dataset(self.args).get_feature()
        self.regression(features, model_cfg=model_cfg, save_model=True)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Train Example')
    parser.add_argument('--config_path', type=str,
                        default='./config/competition.json')
    args = parser.parse_args()

    with open(args.config_path, 'r') as file:
        p_args = argparse.Namespace()
        p_args.__dict__.update(json.load(file))
        args = parser.parse_args(namespace=p_args)

    Train(args).run_regression()
