import numpy as np

class diffraction_format:
    def __init__(self,conf,tof,counts,error, directory, name):
        name_parts = name.split('_')
        name_parts = name_parts[1:-1]
        joined_name = '_'.join(name_parts)
        self.runNo = conf["current_runno"]
        self.bankname = conf["current_bank"]
        self.path = directory+"/"+conf["beamline_name"]+"_" + joined_name
        self.focus_point = conf["focus_point"]
        self.bl = conf['beamline_name']
        self.factor = conf["multiply_factor_fullprof"]
        self.tof = tof
        self.counts = counts
        self.error = error
        self.suffixes = {
            'gsas': ".gsa",
            'fp': ".dat",
            'zr': ".histogramIgor"
        }
        self.filenames = {k: f"{self.path}{v}" for k, v in self.suffixes.items()}

    def update_suffixes(self, conf, name):
        if conf["normByPC"]:
            self.suffixes = {k: "pc" + v for k, v in self.suffixes.items()}
        if conf["time_slice"]:
            slice_suffix = f"{name[-6]}_" if conf['normByPC'] else f'{name[-4]}_'
            self.suffixes = {k: slice_suffix + v for k, v in self.suffixes.items()}

    def create_filenames(self):
        return {k: f"{self.path}_{self.bankname}_{v}" for k, v in self.suffixes.items()}


    def writeGSAS(self):
        CR = chr(13)
        LF = chr(10)
        CRLF = LF
        f_gsas = open(self.filenames['gsas'], "w")
        strtmp = self.bl+" Diffraction Histogram for " + self.bankname + ", " + str(self.runNo)
        f_gsas.write("%-80s%s" % (strtmp, CRLF))

        n = len(self.tof)
        step = self.tof[1] - self.tof[0]
        istart = 1
        for i in range(n - 1):
            if self.tof[i + 1] - self.tof[i] != step:
                istart = i + 1
                break
        res = (self.tof[istart] - self.tof[istart - 1]) / float(self.tof[istart - 1])
        num = self.bankname[:5][-1]
        nrec = 1
        nch = n - 1
        n = nch
        strtmp = "%s%s %6d %6d %s %6d %6d %6d %.6f %s" % (
            "BANK ",
            num,
            n,
            nch,
            "RALF",
            int(self.tof[0]) * 32,
            step * 32,
            int(self.tof[istart]) * 32,
            res,
            "FXYE",
        )
        f_gsas.write("%-80s%s" % (strtmp, CRLF))

        for i in range(nch):
            for j in range(nrec):
                if i * nrec + j == 0:
                    x = self.tof[0]
                else:
                    x = (self.tof[i * nrec + j] + self.tof[i * nrec + j - 1]) * 0.5
                strtmp = "%15.6f %15.10f %15.10f" % (
                    x,
                    self.counts[i * nrec + j] * (self.tof[i * nrec + j + 1] - self.tof[i * nrec + j]),
                    self.error[i * nrec + j] * (self.tof[i * nrec + j + 1] - self.tof[i * nrec + j]),
                )
                f_gsas.write("%s" % strtmp)
            f_gsas.write("%s" % CRLF)
        f_gsas.close()

    def writeFP(self):
        theta2 = self.focus_point[self.bankname[:5]]["2_theta"]
        CR = chr(13)
        LF = chr(10)
        CRLF = LF
        f_fp = open(self.filenames['fp'], "w")

        strtmp = self.bl+" Diffraction Histogram for "+str(theta2)+"-degree bank, " + str(
                self.runNo)  # +', Rexp is '+str(rexp)
        f_fp.write("%s%s" % (strtmp, CRLF))
        strtmp = "The original intensities and sigmas have been multiplied by "+str(10**(self.factor))
        f_fp.write("%s%s" % (strtmp, CRLF))
        strtmp = "%s %s %s" % ("TOF", "INT", "ERR")
        f_fp.write("%s%s" % (strtmp, CRLF))
        # write data
        for i in range(len(self.tof)):
            strtmp = "%.2f %.6f %.6f" % (
                self.tof[i],
                self.counts[i] * (10 ** (self.factor)),
                self.error[i] * (10 ** (self.factor)),
            )
            f_fp.write("%s" % strtmp)
            f_fp.write("%s" % CRLF)
        f_fp.close()

    def writeZR(self):
        CR = chr(13)
        LF = chr(10)
        CRLF = LF
        f_zr = open(self.filenames['zr'], "w")
        strtmp = "IGOR"
        f_zr.write("%s%s" % (strtmp, CRLF))
        strtmp = "%s %s %s %s" % ("WAVES/O", "tof", "yint", "yerr")
        f_zr.write("%s%s" % (strtmp, CRLF))
        strtmp = "BEGIN"
        f_zr.write("%s%s" % (strtmp, CRLF))
        # write data
        for i in range(len(self.tof)):
            strtmp = "%.2f %.6f %.6f" % (self.tof[i], self.counts[i], self.error[i])
            f_zr.write("%s" % strtmp)
            f_zr.write("%s" % CRLF)
        strtmp = "END"
        f_zr.write("%s" % (strtmp))
