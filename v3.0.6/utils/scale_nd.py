import numpy as np
from scipy.integrate import quad_vec
from rongzai.dataSvc import create_dataset

def scale_bkg(dataset,conf):
    unit = dataset.attrs.get("x_unit", None)
    if unit != "wavelength":
        raise ValueError(f"unit should be wavelength, not {unit}")
    task = ScaleBkgNeutronData(dataset)
    return task.run_scale_factors(conf)

def get_scale(dataset,conf):
    unit = dataset.attrs.get("x_unit", None)
    if unit != "wavelength":
        raise ValueError(f"unit should be wavelength, not {unit}")
    task = ScaleBkgNeutronData(dataset)
    return task.get_scale_factors(conf)

class ScaleBkgNeutronData():
    def __init__(self,dataset):
        position = dataset["positions"].values
        if len(position[0]) == 8:
            self.theta = position[:,4] / 360 * np.pi
        else:
            self.theta = 0.5 * np.arccos(position[:,2] / np.sqrt(position[:,0] ** 2 + position[:,1] ** 2 + position[:,2] ** 2))
        self.nd = dataset

    def TT_Func(self, x, d, wave_arr, conf):
        R = conf['radius']

        atten = conf['atten_xs'] * conf['density_num'] * wave_arr  # (n,)
        x = np.asarray(x)

        if x.ndim == 0:
            # 标量 x，返回 (n,)
            s1 = np.sqrt(np.clip(R * R - (R - x) ** 2, 0.0, None))  # 标量
            s2 = np.sqrt(np.clip(R * R - (R - (d - x)) ** 2, 0.0, None))  # 标量
            return np.exp(-atten * 2.0 * s1) * np.exp(-atten * 2.0 * s2)  # (n,)
        else:
            # 向量 x，返回 (k, n)
            x = x[:, None]  # (k,1)
            s1 = np.sqrt(np.clip(R * R - (R - x) ** 2, 0.0, None))  # (k,1)
            s2 = np.sqrt(np.clip(R * R - (R - (d - x)) ** 2, 0.0, None))  # (k,1)
        return np.exp(-atten * 2.0 * s1) * np.exp(-atten * 2.0 * s2)  # (k,n)

    def T_Func(self, x, wave_arr, conf):
        R = conf['radius']

        atten = conf['atten_xs'] * conf['density_num'] * wave_arr  # (n,)
        x = np.asarray(x)

        if x.ndim == 0:
            s = np.sqrt(np.clip(R * R - (R - x) ** 2, 0.0, None))  # 标量
            return np.exp(-atten * 2.0 * s)  # (n,)
        else:
            x = x[:, None]  # (k,1)
            s = np.sqrt(np.clip(R * R - (R - x) ** 2, 0.0, None))  # (k,1)
            return np.exp(-atten * 2.0 * s)  # (k,n)

    def get_scale_factors(self, conf, K=8, chunk=256):
        # 高斯-勒让德定点求积 + 全矢量化/分块, 大大提高积分速度
        # 对每一行 i：
        # 被积函数只通过 s(x) 或 s1(x)+s2(x) 依赖 x、d 和样品半径 R；
        # 波长 wave_arr 只以系数 atten = atten_xs * density_num * wave 参与到 exp(-atten * S(x)) 中；
        # 所以可以先把 S(x) 在每个行的若干个求积点一次性算好，再对不同波长用广播一次性算 exp 并求和。

        # 核心做法：
        # 选定 K 个高斯-勒让德点（通常 32/64/96 即可达到很高精度），把每行不同的积分上限通过仿射映射到这些点；
        # 批量计算 s、s1、s2 和权重，再对所有波长一起做 exp 和加权求和；
        # 为避免内存峰值过大，对行做分块处理（chunk）。

        #性能与精度
        # K=64 往往就能达到 1e-8 量级的精度（与你之前 quad_vec 的误差同量级）。如果需要更快可试 K=32；需要更准可试 K=96/128。
        # chunk 可根据内存调节。构造的最大三维块大小约为 (chunk × K × n)。例如 chunk=256、K=64、n=1000，则中间数组大小约 256×64×1000 ≈ 16M 元素，float64 约 128MB，可按机器内存调节。

        alpha = np.arccos(conf["radius"] / conf["cell_radius"])
        L_AA = 2 * conf["cell_radius"] * (self.theta - alpha)
        L_AA[L_AA < 0] = 0
        R_AA = L_AA / (2 * np.pi * conf["cell_radius"])
        R_A = 1 - 2 / np.pi * alpha - L_AA / np.pi / conf["cell_radius"]
        R_N = 1 - R_A - R_AA

        R = float(conf["radius"])
        Rc = float(conf["cell_radius"])
        c0 = float(conf["atten_xs"]) * float(conf["density_num"])
        c1 = float(conf["scatt_xs"]) * float(conf["density_num"])

        d = (R * (1 - np.cos(L_AA / Rc))
             + np.sqrt(Rc ** 2 - R ** 2) * np.sin(L_AA / Rc))  # (m,)

        wave_all = np.asarray(self.nd["xvalue"].values, dtype=float)  # (m,n) 或 (n,)
        if wave_all.ndim != 2:
            raise ValueError("xvalue 需为二维 (m,n)")

        m, n = wave_all.shape
        TT = np.empty((m, n), dtype=float)
        T = np.empty((m, n), dtype=float)

        # 预计算每个通道的衰减系数：atten = c0 * wavelength
        atten2d = c0 * wave_all + c1  # (m,n)

        # 高斯-勒让德节点/权重（定义在 [-1,1]）
        t, w = np.polynomial.legendre.leggauss(K)  # t,w 形状 (K,)

        # 分块处理行，避免一次性构造 (m,K,n) 过大的数组
        for s in range(0, m, chunk):
            e = min(s + chunk, m)

            d_blk = d[s:e]  # (p,)
            b_blk = np.clip(2 * Rc - d_blk, 0.0, None)  # (p,)  T 的上限
            atten_blk = atten2d[s:e]  # (p,n)

            # ----- TT: ∫_0^{d} exp(-atten * 2*(s1+s2)) dx -----
            # x = 0.5*(t+1)*d_i
            xTT = 0.5 * (t + 1.0) * d_blk[:, None]  # (p,K)
            wTT = 0.5 * d_blk[:, None] * w[None, :]  # (p,K)

            # s1 = sqrt(R^2 - (R - x)^2), s2 = sqrt(R^2 - (R - (d - x))^2)
            s1 = np.sqrt(np.clip(R * R - (R - xTT) ** 2, 0.0, None))  # (p,K)
            s2 = np.sqrt(np.clip(R * R - (R - (d_blk[:, None] - xTT)) ** 2, 0.0, None))
            S_TT = 2.0 * (s1 + s2)  # (p,K)

            # 通过广播计算 exp(-atten * S_TT)
            vals_TT = np.exp(-atten_blk[:, None, :] * S_TT[..., None])  # (p,K,n)
            TT[s:e] = (vals_TT * wTT[..., None]).sum(axis=1)  # (p,n)

            # ----- T: ∫_0^{b} exp(-atten * 2*s) dx -----
            xT = 0.5 * (t + 1.0) * b_blk[:, None]  # (p,K)
            wT = 0.5 * b_blk[:, None] * w[None, :]  # (p,K)
            s_ = np.sqrt(np.clip(R * R - (R - xT) ** 2, 0.0, None))  # (p,K)
            S_T = 2.0 * s_  # (p,K)

            vals_T = np.exp(-atten_blk[:, None, :] * S_T[..., None])  # (p,K,n)
            T[s:e] = (vals_T * wT[..., None]).sum(axis=1)  # (p,n)

        # 合成
        scaleFactors = R_N[:, None] + R_A[:, None] * T + R_AA[:, None] * TT


        module = self.nd.attrs.get("name", None)
        unit = self.nd.attrs.get("x_unit", None)
        err_data = np.zeros(scaleFactors.shape)
        dataset_scale_factors = create_dataset(scaleFactors, err_data, self.nd["xvalue"].values,
                                     self.nd["positions"].coords["pixel"].values,
                                     self.nd["positions"].values,
                                     self.nd['proton_charge'], self.nd['l1'], module, unit)
        return dataset_scale_factors

    def run_scale_factors(self, conf, K=8, chunk=256):
        alpha = np.arccos(conf["radius"] / conf["cell_radius"])
        L_AA = 2 * conf["cell_radius"] * (self.theta - alpha)
        L_AA[L_AA < 0] = 0
        R_AA = L_AA / (2 * np.pi * conf["cell_radius"])
        R_A = 1 - 2 / np.pi * alpha - L_AA / np.pi / conf["cell_radius"]
        R_N = 1 - R_A - R_AA

        R = float(conf["radius"])
        Rc = float(conf["cell_radius"])
        c0 = float(conf["atten_xs"]) * float(conf["density_num"])
        c1 = float(conf["scatt_xs"]) * float(conf["density_num"])

        d = (R * (1 - np.cos(L_AA / Rc))
             + np.sqrt(Rc ** 2 - R ** 2) * np.sin(L_AA / Rc))  # (m,)

        wave_all = np.asarray(self.nd["xvalue"].values, dtype=float)  # (m,n) 或 (n,)
        if wave_all.ndim != 2:
            raise ValueError("xvalue 需为二维 (m,n)")

        m, n = wave_all.shape
        TT = np.empty((m, n), dtype=float)
        T = np.empty((m, n), dtype=float)

        # 预计算每个通道的衰减系数：atten = c0 * wavelength
        atten2d = c0 * wave_all + c1  # (m,n)

        # 高斯-勒让德节点/权重（定义在 [-1,1]）
        t, w = np.polynomial.legendre.leggauss(K)  # t,w 形状 (K,)

        # 分块处理行，避免一次性构造 (m,K,n) 过大的数组
        for s in range(0, m, chunk):
            e = min(s + chunk, m)

            d_blk = d[s:e]  # (p,)
            b_blk = np.clip(2 * Rc - d_blk, 0.0, None)  # (p,)  T 的上限
            atten_blk = atten2d[s:e]  # (p,n)

            # ----- TT: ∫_0^{d} exp(-atten * 2*(s1+s2)) dx -----
            # x = 0.5*(t+1)*d_i
            xTT = 0.5 * (t + 1.0) * d_blk[:, None]  # (p,K)
            wTT = 0.5 * d_blk[:, None] * w[None, :]  # (p,K)

            # s1 = sqrt(R^2 - (R - x)^2), s2 = sqrt(R^2 - (R - (d - x))^2)
            s1 = np.sqrt(np.clip(R * R - (R - xTT) ** 2, 0.0, None))  # (p,K)
            s2 = np.sqrt(np.clip(R * R - (R - (d_blk[:, None] - xTT)) ** 2, 0.0, None))
            S_TT = 2.0 * (s1 + s2)  # (p,K)

            # 通过广播计算 exp(-atten * S_TT)
            vals_TT = np.exp(-atten_blk[:, None, :] * S_TT[..., None])  # (p,K,n)
            TT[s:e] = (vals_TT * wTT[..., None]).sum(axis=1)  # (p,n)

            # ----- T: ∫_0^{b} exp(-atten * 2*s) dx -----
            xT = 0.5 * (t + 1.0) * b_blk[:, None]  # (p,K)
            wT = 0.5 * b_blk[:, None] * w[None, :]  # (p,K)
            s_ = np.sqrt(np.clip(R * R - (R - xT) ** 2, 0.0, None))  # (p,K)
            S_T = 2.0 * s_  # (p,K)

            vals_T = np.exp(-atten_blk[:, None, :] * S_T[..., None])  # (p,K,n)
            T[s:e] = (vals_T * wT[..., None]).sum(axis=1)  # (p,n)

        # 合成
        scaleFactors = R_N[:, None] + R_A[:, None] * T + R_AA[:, None] * TT

        new_data = self.nd["histogram"].values * scaleFactors
        err_data = self.nd["error"].values * scaleFactors

        module = self.nd.attrs.get("name", None)
        unit = self.nd.attrs.get("x_unit", None)
        dataset = create_dataset(new_data, err_data, self.nd["xvalue"].values,
                                     self.nd["positions"].coords["pixel"].values,
                                     self.nd["positions"].values,
                                     self.nd['proton_charge'], self.nd['l1'], module, unit)
        return dataset

if __name__ == "__main__":
    import time
    t0 = time.time()
    from rongzai.dataSvc import load_histogram_data
    from rongzai.algSvc.neutron import convert_unit_elastic
    run_fn = ["D:\Documents\CSNS_data\BL16\RUN0020850\detector.nxs"]
    pidInfo_fn = 'D:\BaiduSyncdisk\Research\My_ongoing_research_or_work\qt_develop\\rzera_offline\param_data\BL16\pidInfo\module10503.txt'
    module = "module10503"
    first_flight_distance = 30
    neutron_data = load_histogram_data(run_fn, pidInfo_fn, module, first_flight_distance, 0.0)
    neutron_data = convert_unit_elastic(neutron_data, "wavelength")
    cal_info = {"radius": 0.448,"cell_radius": 0.448, "atten_xs":2.8, "scatt_xs":5.1 , "density_num":0.0721}
    scale_factors = get_scale(neutron_data, cal_info)
    print(scale_factors['histogram'].values)
    t1 = time.time()
    print("time:", t1-t0)