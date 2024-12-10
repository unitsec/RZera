import numpy as np


class diffraction_format:
    def __init__(self,conf):#, usePC, savePath,beamline_name):
        self.runNo = conf["current_runno"]
        self.bankname = conf["current_bank"]
        #self.bank = self.bankname.upper()
        self.focus_point = conf["focus_point"]
        self.bl = conf['beamline_name']
        self.factor = conf["multiply_factor_fullprof"]

    def writeGSAS(self, tof, counts, error, directory, filename):
        # define output filename
        #filename = self.path+"_"+self.bank+self.suffix_gsas
        CR = chr(13)
        LF = chr(10)
        CRLF = LF
        filepath = directory + '/' + filename + '.gsa'
        f_gsas = open(filepath, "w")
        strtmp = self.bl+" Diffraction Histogram for " + self.bankname + ", " + str(self.runNo)
        f_gsas.write("%-80s%s" % (strtmp, CRLF))

        n = len(tof)
        # mul=1
        step = tof[1] - tof[0]
        istart = 1
        for i in range(n - 1):
            if tof[i + 1] - tof[i] != step:
                istart = i + 1
                break
        res = (tof[istart] - tof[istart - 1]) / float(tof[istart - 1])
        # write keyword
        # iformat = 2
        num = self.bankname[-1]
        nrec = 1
        nch = n - 1
        n = nch
        strtmp = "%s%s %6d %6d %s %6d %6d %6d %.6f %s" % (
            "BANK ",
            num,
            n,
            nch,
            "RALF",
            int(tof[0]) * 32,
            step * 32,
            int(tof[istart]) * 32,
            res,
            "FXYE",
        )
        f_gsas.write("%-80s%s" % (strtmp, CRLF))

        # write data
        for i in range(nch):
            for j in range(nrec):
                if i * nrec + j == 0:
                    x = tof[0]
                else:
                    x = (tof[i * nrec + j] + tof[i * nrec + j - 1]) * 0.5
                strtmp = "%15.6f %15.10f %15.10f" % (
                    x,
                    counts[i * nrec + j] * (tof[i * nrec + j + 1] - tof[i * nrec + j]),
                    error[i * nrec + j] * (tof[i * nrec + j + 1] - tof[i * nrec + j]),
                )
                f_gsas.write("%s" % strtmp)
            f_gsas.write("%s" % CRLF)
        f_gsas.close()

    def writeFP(self, tof, counts, error, directory, filename):
        theta2 = self.focus_point[self.bankname]["2_theta"]
        # filename = self.path+"_"+self.bank+self.suffix_fp
        CR = chr(13)
        LF = chr(10)
        CRLF = LF
        filepath = directory + '/' + filename + '.dat'
        f_fp = open(filepath, "w")
        # f_fp = open(self.filenames['fp'], "w")

        strtmp = self.bl+" Diffraction Histogram for "+str(theta2)+"-degree bank, " + str(
                self.runNo)  # +', Rexp is '+str(rexp)
        f_fp.write("%s%s" % (strtmp, CRLF))
        strtmp = "The original intensities and sigmas have been multiplied by "+str(10**(self.factor))
        f_fp.write("%s%s" % (strtmp, CRLF))
        strtmp = "%s %s %s" % ("TOF", "INT", "ERR")
        f_fp.write("%s%s" % (strtmp, CRLF))
        # write data
        for i in range(len(tof)):
            strtmp = "%.2f %.6f %.6f" % (
                tof[i],
                counts[i] * (10 ** (self.factor)),
                error[i] * (10 ** (self.factor)),
            )
            f_fp.write("%s" % strtmp)
            f_fp.write("%s" % CRLF)
        f_fp.close()

    def writeZR(self, tof, counts, error, directory, filename):
        #filename = self.path+"_"+bank+self.suffix_zr
        CR = chr(13)
        LF = chr(10)
        CRLF = LF
        filepath = directory + '/' + filename + '.histogramIgor'
        f_zr = open(filepath, "w")
        # f_zr = open(self.filenames['zr'], "w")
        strtmp = "IGOR"
        f_zr.write("%s%s" % (strtmp, CRLF))
        strtmp = "%s %s %s %s" % ("WAVES/O", "tof", "yint", "yerr")
        f_zr.write("%s%s" % (strtmp, CRLF))
        strtmp = "BEGIN"
        f_zr.write("%s%s" % (strtmp, CRLF))
        # write data
        for i in range(len(tof)):
            strtmp = "%.2f %.6f %.6f" % (tof[i], counts[i], error[i])
            f_zr.write("%s" % strtmp)
            f_zr.write("%s" % CRLF)
        strtmp = "END"
        f_zr.write("%s" % (strtmp))

