import numpy as np
import subprocess
import os
import pandas as pd
import re

SUFFIXES = {'maize': '.MZX', 'rice': '.RIX'}
CUL_NAME = {'maize': 'MZCER047', 'rice': 'RICER047'}
RE_SUFFIXES = {v: k for k, v in SUFFIXES.items()}
import torch

torch.nn.Module()


class DSSAT(object):
    def __init__(self, x_file, run_path_absolute=r'C:\DSSAT47'):
        """
        Initializes necessary params from single x_file and Dssat installed directory.
        :param x_file: The absolute path to .cuXf ile
        :param run_path_absolute: The absolute path to Dssat installed directory
        """
        # The path of the DSCSM047.EXE
        self._run_path = run_path_absolute
        # Consist of /dir/_file_name.cuX
        self._base_name = os.path.basename(x_file)
        # Only prefix of basename without suffix.
        self._file_name = os.path.splitext(self._base_name)[0]
        self._crop_type = RE_SUFFIXES[os.path.splitext(self._base_name)[-1]]
        self._genotype_file_path = os.path.join(self._run_path, 'Genotype', '%s.CUL' % CUL_NAME[self._crop_type])
        self._crop_path = os.path.join(self._run_path, self._crop_type.capitalize())
        # make soft link to x_file in DEFAULT CROP FILE
        if self._crop_path != os.path.dirname(x_file):
            os.system(r'copy /Y %s %s > c:\Windows\nul' % (x_file, os.path.join(self._crop_path, self._base_name)))
        self.pwd = os.getcwd()
        print('\n### Current crop: %s , filename: %s' % (self._crop_type, self._file_name))

    def run_glue(self, epochs, glue_flag=1):
        """
        First ,change the params of config files in /DSSAT/GLWork
        Second ,Calling R program to run GLUE.
        Third ,rewrite the .CUL genotype file.
        :param epochs:
        :param glue_flag:
        :return:
        """
        if not isinstance(epochs, int):
            epochs = int(epochs)
        print('\n\tRunning Glue (with epochs: %d)......' % epochs)
        glue_work = os.path.join(self._run_path, 'GLWork')
        glue_path = os.path.join(self._run_path, 'Tools', 'GLUE')

        def _create_batch(ingeno, cname, treatments, group_begin_idx):
            file = []
            file.append('$BATCH(CULTIVAR):%s%s %s' % (SUFFIXES[self._crop_type][1:3], ingeno, cname))
            file.append(' ')
            file.append(
                '@FILEX%88sTRTNO     RP     SQ     OP     CO' % '')
            group_end_idx = group_begin_idx
            for i in range(len(treatments)):
                group_end_idx += 1
                file.append(
                    '%-50s%49s      0      0      0      0' % (
                        os.path.join(self._crop_path, self._file_name + SUFFIXES[self._crop_type]),
                        group_begin_idx + i + 1))

            with open(os.path.join(glue_work, cname.replace(' ', '_') + SUFFIXES[self._crop_type])[:-1] + 'C',
                      'w') as fp:
                fp.write('\n'.join(file) + '\n')
            return group_end_idx

        # control the treatment_id in the xfile
        group_begin_idx = 0
        for ingeno, cname, treatments in zip(*self._search_treatments()):

            # Check whether target ingeno is in Genotype.
            # If ingeno exists, continue ,else ,add at end
            encoding = "utf-8"
            if self._crop_type == 'rice':
                encoding = 'gbk'
            with open(self._genotype_file_path, 'r+', encoding=encoding) as fp:
                lines = fp.read()
                if ingeno not in lines or cname not in lines:
                    if self._crop_type == 'maize':
                        fp.write('{ingeno:6} {cname:<21}. IB0001 120.0 0.000 685.0 907.9 10.00 38.90\n'.format(
                            ingeno=ingeno, cname=cname))
                    elif self._crop_type == 'rice':
                        fp.write(
                            '{ingeno:6} {cname:<21}. IB0001 880.0  52.0 550.0  12.1  65.0 .0280  1.00  1.00  83.0   1.0\
                            \n'.format(ingeno=ingeno, cname=cname))
                    else:
                        print('\n Warning This crop is unsupportable now!!!')
                        return

            for fn in os.listdir(glue_work):
                if os.path.isfile(os.path.join(glue_work, fn)):
                    os.remove(os.path.join(glue_work, fn))
            group_begin_idx = _create_batch(ingeno, cname, treatments, group_begin_idx)
            with open(os.path.join(glue_path, 'Glue.r'), 'r') as fp:
                text = fp.read()
            text = re.sub('CultivarBatchFile<-[^;]+";?',
                          'CultivarBatchFile<-"%s";' % (cname.replace(' ', '_') + SUFFIXES[self._crop_type][:-1] + 'C'),
                          text)
            with open(os.path.join(glue_path, 'Glue.r'), 'w') as fp:
                fp.write(text)
            del text

            df = pd.read_csv(os.path.join(glue_path, 'SimulationControl.csv'))
            df.iloc[0, 1] = epochs
            df.iloc[1, 1] = glue_flag
            df.to_csv(os.path.join(glue_path, 'SimulationControl.csv'), index=None)
            os.chdir(self._run_path)
            with open(os.path.join(glue_work, 'stdout.txt'), 'w') as fp:
                subprocess.call(r'"C:\Program Files\R\R-3.4.0\bin\R.exe" --slave < C:\dssat47\Tools\Glue\Glue.r',
                                stdout=fp)
            with open(os.path.join(glue_work, '%s%s.CUL'
                                              % (SUFFIXES[self._crop_type][1:3], ' '.join([ingeno, cname]))),
                      'r') as f:
                line = f.readline()
            print('\n\tFinished Cultivar : %s......' % ingeno)
            with open(self._genotype_file_path, 'r')as fr:
                text = fr.read()
            if line[:26] not in text:
                text = text + '\n' + line + '\n'
                print('New line:%s has added' % line)
            else:
                # some char in cname such as +,(,)* can't be recognized by re, then I choose first 9 chars in line
                text = re.sub('%s[^\n]+\n?' % (line[:10]), line, text)
            with open(self._genotype_file_path, 'w') as fw:
                fw.write(text)
        os.chdir(self.pwd)

    def _search_treatments(self):
        with open(os.path.join(self._crop_path, self._base_name), 'r', encoding='utf-8') as fp:
            ingenos, cnames, treatments = {}, {}, {}
            line = fp.readline()
            while line != '':
                if '@N R O C TNAME' in line:
                    line = fp.readline()
                    while line != '\n':
                        treatments.update({line[9:34].strip(): line[36:38].strip()})
                        line = fp.readline()
                    continue
                if '@C CR INGENO CNAME' in line:
                    line = fp.readline()
                    while line != '\n':
                        ingenos.update({line[6:12]: line[:2].strip()})
                        cnames.update({line[:2].strip(): line[13:].strip()})
                        line = fp.readline()
                    continue
                line = fp.readline()
        ings = ingenos.keys()
        cns = [cnames[ingenos[ing]] for ing in ings]
        tms = {i: [] for i in np.unique(list(treatments.values()))}
        for tm, idx in treatments.items():
            tms[idx].append(tm)
        return ings, cns, [tms[ingenos[ing]] for ing in ings]

    def create_DSSBatch(self):
        """
        crop_type: The type of crop to be simulated. Now supported : 'maize','rice'.
        At present ，I find that the model can't run without .x and .v47 in the main corp file, such as Maize,Wheat.
        :return:
        """

        print('\n\tCreating DSSBatch.v47 file......')
        lines = []
        lines.append('$BATCH(%s)' % self._crop_type.upper())
        lines.append('!')
        lines.append('! Crop         : %s' % self._crop_type.capitalize())
        lines.append('! Shengyang Agricultural University  Qianchuan Mi')
        lines.append('! ExpNo        : 1')
        lines.append('')
        lines.append(
            '@FILEX                                                                                        TRTNO     RP     SQ     OP     CO')

        name_list = []
        variety_numbers = {}
        fn = self._base_name
        if SUFFIXES[self._crop_type.lower()] == os.path.splitext(fn)[-1]:
            name_list.append(fn)
            with open(os.path.join(self._crop_path, fn), 'r', encoding='utf-8') as fp:
                while True:
                    if '@N R O C TNAME.................... CU FL SA IC MP MI MF MR MC MT ME MH SM' in fp.readline():
                        nums = 0
                        while '\n' != fp.readline():
                            nums += 1
                        variety_numbers[fn] = nums
                        break

        for i in range(len(name_list)):
            for j in range(variety_numbers[name_list[i]]):
                lines.append(
                    '%-98s%s      1      0      0      0' % (
                        os.path.join(self._crop_path, name_list[i]), j + 1))

        fname = os.path.join(self._crop_path, 'DSSBatch.v47')
        with open(fname, 'w') as f:
            f.write('\n'.join(lines))
        print('\n\tDSSBatch.v47 Created successfully ! ')

    def run(self, output_path, simulation_model='B'):
        '''
        :param:output_path:The directory to keep evaluated outputs.Absolutely path is recommended.
        :param:simulation_model:
            B – Batch, for use with conventional single treatment, single season *.crX files,
                where “cr” represents a DSSAT crop code (e.g., WH).
            N – Seasonal, for use with *.SNX files
            Q – Sequence, for use with *.SQX files
            S – Spatial, for use witn *.GSX files

        '''
        print('\n\tRunning DSSAT model......')
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        output_path = os.path.join(output_path, self._crop_type)
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        output_path = os.path.join(output_path, self._file_name)
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        exe_path = os.path.join(self._run_path, 'DSCSM047.EXE')
        batch_path = os.path.join(self._crop_path, 'DSSBatch.v47')

        with open(os.path.join(output_path, 'out.txt'), mode='w', encoding='utf-8') as f:
            # os.chdir will change the work directory
            # Change the place of this command will figure out problems with relative path
            os.chdir(output_path)
            subprocess.check_call([exe_path, os.path.basename(self._genotype_file_path), simulation_model, batch_path],
                                  shell=True, stdout=f)
            print('\n\tRunning successful! With result in %s' % os.getcwd())
            os.chdir(self.pwd)

    def __call__(self, out_path, gl_epochs, glue_flag=1, simulation_model='B'):
        """
        :param out_path: The directory to keep evaluated outputs,Absolutely path is recommended.
        :param gl_epochs: The epochs to run glue
        :return:
        """
        # STEP1 : RUN GLUE
        self.run_glue(gl_epochs, glue_flag)

        # STEP2 : CREATE DSSBatch FILE
        self.create_DSSBatch()

        # STEP3 : RUN DSSAT
        self.run(out_path, simulation_model)

        # STEP4 : DELETE USELESS FILES

        # STEP5 : EXTRACT AVAILABLE FILES


if __name__ == '__main__':
    dssat = DSSAT(r'output/UAFD0011.RIX')
