import datetime
import datetime as dt
import numpy as np
import pandas as pd

GROWTH_STAGE_LIST = ['seedling_stage', 'survival&jointing_stage', 'tillering_stage', 'reproductive_growth_stage',
                     'maturity_stage']
GROWTH_STAGE_GDD_LIST = [384, 584, 1206, 1502, 2102]


def get_growth_stage(method='gdd', **kwargs):
    if method == 'gdd':
        growth_stage_gdd_list = [384, 584, 1206, 1502, 2102]
        # 根据积温返回生育期,从播种开始计算
        acc_tmp = 0
        for k, v in kwargs.items():
            if k == 'acc_tmp':
                acc_tmp = float(v)
        if acc_tmp < growth_stage_gdd_list[0]:
            return GROWTH_STAGE_LIST[0]
        elif acc_tmp < growth_stage_gdd_list[1]:
            return GROWTH_STAGE_LIST[1]
        elif acc_tmp < growth_stage_gdd_list[2]:
            return GROWTH_STAGE_LIST[2]
        elif acc_tmp < growth_stage_gdd_list[3]:
            return GROWTH_STAGE_LIST[3]
        elif acc_tmp < growth_stage_gdd_list[4]:
            return GROWTH_STAGE_LIST[4]
        else:
            return 'end'


def get_gdd(tmp):
    t_b = 10
    t_m = 40
    if tmp > t_m:
        tmp = t_m
    elif tmp < t_b:
        tmp = t_b
    return tmp - t_b


class EnvironmentState:

    def __init__(self):
        self.pre = 0
        self.tmp = 0
        self.pre_f = []
        self.tmp_f = []

    def update(self, fs):
        self.pre = fs['precipitation']
        self.tmp = fs['temperature']
        self.pre_f = fs['precipitation_forecast']
        self.tmp_f = fs['temperature_forecast']


class Crop:
    def __init__(self, sd):
        self.acc_tmp = 0
        self.seeding_date = sd
        self.growth_stage = 'seedling_stage'

    def manual_update(self, pgs):
        # 根据巡田结果更新作物生育期
        pass

    def daily_update(self, tmp):
        # 根据每日气温更新作物积温和生育期，返回当前生育期和积温
        self.acc_tmp = self.acc_tmp + get_gdd(tmp)
        self.growth_stage = get_growth_stage(method='gdd', acc_tmp=self.acc_tmp)
        return self.acc_tmp, self.growth_stage

    def batch_update(self, tmp_list):
        # 批量更新积温
        pass


class CropManagement:
    GROWTH_STAGE_FARMING_ACTIVITIES = {'seedling_stage': ['ploughing', 'base_fert', 'transplanting'],
                                       'tillering_stage': ['tillering_fert'],
                                       'reproductive_growth_stage': ['end_tillering_drying', 'panicle_fert'],
                                       'maturity_stage': ['before_harvest_drying', 'harvest']}

    def __init__(self, sd, init_date, growth_stage_method='gdd'):
        self.seeding_date = sd
        self.crop = Crop(sd)
        self.init_date = init_date
        self.update_date = init_date
        self.growth_stage_method = growth_stage_method
        print("-------------------------------------------------更新农事名称：%-25s 更新农事日期：%s--------更新日期：%s" % (
        '播种', str(sd), str(sd)))

        # 农事时间
        self.transplanting_date = ''
        self.base_fert_date = ''
        self.ploughing_date = ''
        self.tillering_fert_date = ''
        self.end_tillering_drying_date = ''
        self.panicle_fert_date = ''
        self.harvest_date = ''
        self.before_harvest_drying_date = ''
        # self.get_status()

    def update_management_date(self, n, v, td):
        # 动态更新农事时间
        if v <= td:
            return
        if hasattr(self, n) and getattr(self, n) != v:
            setattr(self, n, v)
            print(
                "-------------------------------------------------更新农事名称：%-25s 更新农事日期：%s--------更新日期：%s" % (
                n, str(v), str(td)))
            # self.get_status()

    def update_seedling_stage(self, cdt, ftd, pl):
        """
        更新移栽相关农事
        # 逻辑1：根据推测移栽日期，前2后3天去降水量最小的为移栽日期
        # 逻辑2：距离移栽5天内不更新整地和基肥日期
        # 逻辑3：整地和基肥时间尽量靠近移栽时间
        :param cdt: 当前日期
        :param ftd: 推测移栽日期距今天数,>=1
        :param pl: 未来降水量预测结果
        :return:
        """
        ftd -= 1
        trans_num_min = max(ftd - 2, 0)
        trans_num_max = min(ftd + 3, len(pl))
        # 确定最小降水量日期
        trans_num_pre_list = pl[trans_num_min:trans_num_max]
        min_pre_num = trans_num_pre_list.index(min(trans_num_pre_list))
        days_a = trans_num_min + min_pre_num
        if days_a >= 4:
            # 更新ploughing和base_fert
            base_fert_pre_list = pl[:days_a]
            base_fert_min_pre_num = base_fert_pre_list.index(min(base_fert_pre_list))
            temp_bfd = cdt + dt.timedelta(days=base_fert_min_pre_num + 1)
            self.update_management_date('ploughing_date', cdt + dt.timedelta(days=base_fert_min_pre_num), cdt)
            self.update_management_date('base_fert_date', temp_bfd, cdt)

        temp_td = cdt + dt.timedelta(days=days_a + 1)
        self.update_management_date('transplanting_date', temp_td, cdt)

    def update_tillering_stage(self, cdt, std, pl):
        """
        更新分蘖相关农事
        # 逻辑1：分蘖肥在分蘖始期后1-4天内选择降水量最小的日期
        :param cdt: 当前日期
        :param std: 推测分蘖始期距今天数,>=1
        :param pl: 未来降水量预测结果
        :return:
        """
        # 根据GDD阈值确定分蘖始期日期
        std = std - 1
        tiller_num_min = std + 1
        tiller_num_max = min(std + 4, len(pl))
        # 根据最小降水量日期更新分蘖肥时间
        tiller_num_pre_list = pl[tiller_num_min:tiller_num_max]
        min_pre_num = tiller_num_pre_list.index(min(tiller_num_pre_list))
        days_a = tiller_num_min + min_pre_num
        temp_td = cdt + dt.timedelta(days=days_a + 1)
        self.update_management_date('tillering_fert_date', temp_td, cdt)

    def update_reproductive_growth_stage(self, cdt, pdd, pl):
        """
        更新生殖生长期相关农事
        # 逻辑1：pdd小于3天不更新晒田时间，晒田在幼穗分化前3天开始
        # 逻辑2：穗肥在幼穗分化后1-5天降水量最小日期实施
        :param cdt: 当前日期
        :param pdd: 预测幼穗分化期距今天数，>=1
        :param pl: 未来降水量预测结果
        :return:
        """
        pdd -= 1
        if pdd > 2:
            self.update_management_date('end_tillering_drying_date', cdt + dt.timedelta(days=pdd - 2), cdt)
        rg_num_min = pdd
        rg_num_max = min(pdd + 5, len(pl))
        # 根据最小降水量日期更新穗肥时间
        rg_num_pre_list = pl[rg_num_min:rg_num_max]
        min_pre_num = rg_num_pre_list.index(min(rg_num_pre_list))
        days_a = rg_num_min + min_pre_num
        self.update_management_date('panicle_fert_date', cdt + dt.timedelta(days=days_a + 1), cdt)

    def update_maturity_stage(self, cdt, fmd, pl):
        """
        更新成熟期相关农事
        # 逻辑1：收获日期在完熟期前2后3内降水量最低日期
        # 逻辑2：收获日期距今7天内不更新收获日期
        :param cdt: 当前日期
        :param fmd: 预测完熟日期距今天数,>=1
        :param pl: 未来降水量预测结果
        :return:
        """

        fmd -= 1
        # 收获范围为成熟-1-3
        ha_num_min = max(fmd - 2, 0)
        ha_num_max = min(fmd + 3, len(pl))
        # 根据最小降水量日期更新穗肥时间
        ha_num_pre_list = pl[ha_num_min:ha_num_max]
        min_pre_num = ha_num_pre_list.index(min(ha_num_pre_list))
        days_a = ha_num_min + min_pre_num
        if days_a + 1 > 7:
            self.update_management_date('before_harvest_drying_date', cdt + dt.timedelta(days=days_a - 6), cdt)
            self.update_management_date('harvest_date', cdt + dt.timedelta(days=days_a + 1), cdt)

    def daily_update(self, date, envs):
        date = dt.date(int(date.split('-')[0]), int(date.split('-')[1]), int(date.split('-')[2]))
        self.update_date = date
        crop_c_acc_tmp, crop_c_stage = self.crop.daily_update(envs.tmp)
        if self.growth_stage_method == 'gdd':
            #     预测未来生育期
            f_gdd_list = np.cumsum([get_gdd(i) for i in envs.tmp_f])
            pred_gdd_list = crop_c_acc_tmp + f_gdd_list
            pred_gdd_min = pred_gdd_list[0]
            pred_gdd_max = pred_gdd_list[-2]
            if pred_gdd_list[7] > GROWTH_STAGE_GDD_LIST[-1]:
                return 'over'
            for index, value in enumerate(GROWTH_STAGE_GDD_LIST):
                if pred_gdd_min < value <= pred_gdd_max:
                    flag_list = pred_gdd_list >= value
                    days = int(np.argmax(flag_list == True)) + 1
                    if index == 0:
                        self.update_seedling_stage(date, days, envs.pre_f)
                    elif index == 1:
                        self.update_tillering_stage(date, days, envs.pre_f)
                    elif index == 2:
                        self.update_reproductive_growth_stage(date, days, envs.pre_f)
                    elif index == 4:
                        self.update_maturity_stage(date, days, envs.pre_f)
            else:
                print("当前日期：{0}，作物状态：{1}".format(str(date), crop_c_stage))
            return 'continue'

    def get_status(self):
        print("播种时间：{0} ,  整地时间：{1} , 施基肥时间：{2}, 移栽时间：{3} \n"
              "分蘖肥时间：{4} , 晒田时间：{5} , 穗肥时间：{6} , 晒田时间：{7} \n"
              "收获时间：{8}   ,更新时间：{9}".format(str(self.seeding_date), str(self.ploughing_date),
                                                    str(self.base_fert_date), str(self.transplanting_date),
                                                    str(self.tillering_fert_date), str(self.end_tillering_drying_date),
                                                    str(self.panicle_fert_date), str(self.before_harvest_drying_date),
                                                    str(self.harvest_date), str(self.update_date)
                                                    ))


if __name__ == '__main__':
    weather_data = pd.read_csv('2020_weather.csv', index_col=0)
    weather_data.columns = ['date', 'temp', 'prec']

    # 输入数据：播种时间和气象预测天数
    seeding_date = '2020-06-07'
    weather_forecasting_num = 15

    test_env = EnvironmentState()
    test_crop = CropManagement(seeding_date, seeding_date)
    wd = weather_data.query("date>='{0}'".format(seeding_date)).copy()
    wd.reset_index(inplace=True, drop=True)
    for index, row in wd.iterrows():
        temp_date = row['date']
        c_tmp = row['temp']
        c_pre = row['prec']
        temp_f = wd.iloc[index + 1:index + weather_forecasting_num + 1, 1].values.tolist()
        prec_f = wd.iloc[index + 1:index + weather_forecasting_num + 1, 2].values.tolist()
        test_env.update({"temperature": c_tmp, "precipitation": c_pre, "precipitation_forecast": prec_f,
                         "temperature_forecast": temp_f})
        rt = test_crop.daily_update(temp_date, test_env)
        if 'over' == rt:
            break
