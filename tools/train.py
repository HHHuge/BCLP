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

import xgboost
from xgboost import XGBRegressor

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.getcwd()))
from dataset.dataset import Dataset
from averaging_model import AveragingModels
warnings.filterwarnings('ignore')





class Train:
    """
    训练类
    """

    def __init__(self, args):
        """
        初始化
        :param args: 初始化信息
        """
        self.model = None
        self.args = args

    def regression(self, datasets, regression_type, log_target=True, model_cfg=None, save_model=False):
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
        x_train, y_train = datasets.get("train")
        # regr = KernelRidge(**model_cfg)

        regr = AveragingModels([ElasticNet(**model_cfg["ElasticNet"]),
                                KernelRidge(**model_cfg["KernelRidge"]),
                                xgboost.XGBRegressor(**model_cfg["XGBRegressor"]),
                                ])

        # labels/ targets might be converted to log version based on choice
        targets = np.log(y_train) if log_target else y_train
        # fit regression model
        regr.fit(x_train, targets)
        # predict values/cycle life for all three sets
        pred_train = regr.predict(x_train)

        if log_target:
            # scale up the preedictions
            pred_train = np.exp(pred_train)

        # mean percentage error (same as paper)
        error_train = mean_absolute_percentage_error(y_train, pred_train) * 100
        if save_model:
            joblib.dump(regr, f"./model/{regression_type}_regression.pkl")
        else:
            self.model = regr
        print(f"Regression Error (Train): {error_train}%")

    def run_regression(self):
        """
        训练回归模型主参数
        """
        model_cfg = self.args.model_cfg
        features = Dataset(self.args, regression_type="full").get_feature()
        self.regression(features, regression_type="full", model_cfg=model_cfg,
                        log_target=self.args.log_target, save_model=True)


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
