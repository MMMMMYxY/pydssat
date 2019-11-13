import numpy as np
import subprocess
import os
import pandas as pd
import re
import sys
from collections import OrderedDict
import numpy as np

SUFFIXES = {'maize': '.MZX', 'rice': '.RIX'}
CUL_NAME = {'maize': 'MZCER047', 'rice': 'RICER047'}


class Dssat(object):
    def __init__(self, site_path_absolute, run_path_absolute=r'C:\DSSAT47'):
        '''
        :param run_path_absolute:
            The path of the DSCSM047.EXE ,which is the main file of Dssat
        :param site_path_absolute:
            The path of X-files to create Batch file, which will contain different years as directories.
            Example: r'C:\DSSAT47\site_path
            The structure of directory should like as follow:
            -SITE_FILE
                --STATION_NAME
                    ---CROP_FILE_1
                        ----2018
                        ----2017
                        ...
                    ---WEATHER
            ...


        '''
        # The path of the DSCSM047.EXE
        self._run_path = run_path_absolute
        # The path of the SITE DOCUMENT
        self._site_path = os.path.join(site_path_absolute)
        self._site_weather_path = os.path.join(self._site_path, 'weather')

        if not os.path.exists(site_path_absolute):
            os.mkdir(site_path_absolute)
        if not os.path.exists(self._site_path):
            os.mkdir(self._site_path)
        if not os.path.exists(self._site_weather_path):
            os.mkdir(self._site_weather_path)

    def get_weather(self, lat, lon, data_path, year_range):
        # return station_id
        pass

    def get_soil(self, soil_path, country_name, lat_input, lon_input, site_path):
        # get the soil_id which is the nearest aera of the station
        with open(soil_path) as fp:
            lines = fp.readlines()

        _lat, _lon, _idx = [], [], []
        # get latitude and longitude
        for idx, line in enumerate(lines):
            if ' %s ' % country_name in line:
                alter = line.split()  # split str to words list
                _lat.append(alter[2])  # get lat date
                _lon.append(alter[3])  # get lon date
                _idx.append(idx)
        _lat = np.array(_lat)
        _lon = np.array(_lon)
        # find nearest site of lat_input and lon_input by euclidean distance
        dist = (_lat.astype(float) - lat_input) ** 2 + (_lon.astype(float) - lon_input) ** 2
        _idx_idx = _idx[np.argmin(dist)[0]]
        line_idx = _idx[_idx_idx]
        if _idx_idx == len(_idx) - 1:
            soil_data = lines[line_idx - 2:]
        else:
            soil_data = lines[line_idx - 2:_idx[_idx_idx + 1] - 3]

        soil_data_name = soil_path[0].split()[0]
        with open(site_path + '%s.SOI' % soil_data_name, 'w') as fp:
            fp.write(soil_data)

        subprocess.call(['ln', '-sf', soil_path, soil_path + '%s.SOI' % soil_data_name], shell=True)

    def _create_xfile_text(file_name, ):
        pass

    def create_xfile(self, ):
        # create base file in 'site_crop_path/year_idx'
        # copy (maybe hyperlink) base file in main 'run_path/corp file', such as Maize,Wheat.
        pass

    def create_DSSBatch(self):
        '''

        :param crop_type: The type of crop to be simulated. Now supported : 'maize','rice'.
            At present ，I find that the model can't run without .x and .v47 in the main corp file, such as Maize,Wheat.
        '''
        print('Creating DSSBatch.v47 file......')
        lines = []
        lines.append('$BATCH(%s)' % self._crop_type.upper())
        lines.append('!')
        lines.append('! Crop         : %s' % self._crop_type.capitalize())
        lines.append('! Shengyang Agricultural University  Qianhaun Mi')
        lines.append('! ExpNo        : 1')
        lines.append('')
        lines.append(
            '@FILEX                                                                                        TRTNO     RP     SQ     OP     CO')

        name_list = []
        variety_numbers = {}
        for fn in os.listdir(self._station_crop_path):
            if SUFFIXES[self._crop_type.lower()] == os.path.splitext(fn)[-1]:
                name_list.append(fn)
                with open(os.path.join(self._station_crop_path, fn)) as fp:
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

    def run_glue(self, start_epochs, end_epochs, glue_flag=1):
        '''
        We choose the best performed CUL file by Cycle training.
        :param start_epochs: the left end point of your cycle.
        :param end_epochs: the right end point of your cycle.
        :param glue_flag: change the glue flag.
        :return:
        '''
        print('Running Glue......')
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

        def _eval_model(line):
            line = line.replace('\n', '').strip()
            line = re.sub('\s+', ' ', line)
            dataset = line.split(' ')[-6:]
            print('WARNING : UNFINISHED METHOD EVAL_MODEL')
            return 1

        # control the treatment_id in the xfile
        group_begin_idx = 0
        for ingeno, cname, treatments in zip(self._ingenos, self._cnames, self._treatments_groups):
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
            best_line, best_dist = '', float('inf')

            for epochs in range(start_epochs, end_epochs + 1):
                df = pd.read_csv(os.path.join(glue_path, 'SimulationControl.csv'))
                df.iloc[0, 1] = epochs
                df.iloc[1, 1] = glue_flag
                df.to_csv(os.path.join(glue_path, 'SimulationControl.csv'), index=None)
                os.chdir(self._run_path)
                with open(os.path.join(glue_work, 'stdout.txt'), 'w') as fp:
                    subprocess.call(r'"C:\Program Files\R\R-3.4.0\bin\R.exe" --slave < C:\dssat47\Tools\Glue\Glue.r',
                                    stdout=fp)
                sys.stderr.write(
                    '\r Now running model: EPOCHS : %s/%s | cultivar :%s' % (
                        epochs + 1 - start_epochs, end_epochs + 1 - start_epochs, ingeno + ' ' + cname))
                sys.stderr.flush()
                with open(os.path.join(glue_work, '%s%s.CUL'
                                                  % (SUFFIXES[self._crop_type][1:3], ' '.join([ingeno, cname]))),
                          'r') as f:
                    line = f.readline()
                dist = _eval_model(line)
                if dist < best_dist:
                    best_dist = dist
                    best_line = line

            sys.stderr.write('\n')
            with open(self._genotype_file_path, 'r')as fr:
                text = fr.read()
            try:
                assert best_line[:26] in text
            except Exception as e:
                print('%s not in Genotype file , please add manual', e)
            else:
                # some char in cname such as +,(,)* can't be recognized by re, then I choose first 9 chars in line
                text = re.sub('%s[^\n]+\n?' % (best_line[:10]), best_line, text)
                with open(self._genotype_file_path, 'w') as fw:
                    fw.write(text)

    def run(self, output_file, simulation_model='B', genotype=''):
        '''
        :param:
        simulation_model:
            B – Batch, for use with conventional single treatment, single season *.crX files,
                where “cr” represents a DSSAT crop code (e.g., WH).
            N – Seasonal, for use with *.SNX files
            Q – Sequence, for use with *.SQX files
            S – Spatial, for use witn *.GSX files

        '''
        print('Running DSSAT model......')
        if not os.path.exists(output_file):
            os.mkdir(output_file)
        os.chdir(output_file)
        # subprocess.call(['ln', '-sf', os.path.join(self.run_path ,'DSCSM047.EXE'), self.site_path])
        exe_path = os.path.join(self._run_path, 'DSCSM047.EXE')
        batch_path = os.path.join(self._crop_path, 'DSSBatch.v47')
        with open(os.path.join(self._station_path, 'out.txt'), 'w') as f:
            subprocess.check_call([exe_path, genotype, simulation_model, batch_path], shell=True, stdout=f)

    def __call__(self, crop_type, station, ingenos, cnames, file_name, year_idx, treatments_1, *args):
        '''

        :param crop_type: Now supported : 'maize','rice'.
        :param year_idx: The simulation year , as well as the year of WEATHER DATA
        :return:
        '''
        # ########## STEP 1 : PREPARE FOR PRE-SETTING VARIABLES (INITIALIZE) ##########
        self._crop_type = crop_type.lower()
        # Main crop file
        self._crop_path = os.path.join(self._run_path, crop_type.lower().capitalize())
        self._station_path = os.path.join(self._site_path, station)
        self.year_idx = year_idx
        self._station_crop_path = os.path.join(self._station_path, crop_type.lower())
        self._ingenos = ingenos.split(',')
        self._cnames = cnames.split(',')
        self._treatments_groups = [treatments_1.split(',')]
        for arg in args:
            self._treatments_groups.append(arg.split(','))
        self._genotype_file_path = os.path.join(self._run_path, 'Genotype', '%s.CUL' % CUL_NAME[self._crop_type])
        self._file_name = file_name
        if not os.path.exists(self._station_path):
            os.mkdir(self._station_path)
        if not os.path.exists(self._station_crop_path):
            os.mkdir(self._station_crop_path)
        # Update _station_crop_path to crop_file/year_idx
        self._station_crop_path = os.path.join(self._station_crop_path, self.year_idx)
        if not os.path.exists(self._station_crop_path):
            os.mkdir(self._station_crop_path)

        # ########## STEP 2 : CREATING OR SETTING SIMULATION NEEDED FILES ##########
        self.run_glue(1, 1)
        self.create_DSSBatch()

        # ########## STEP 3 : RUN DSSAT ##########
        self.run(r'C:\out', genotype=CUL_NAME[self._crop_type])

        print('Complete Successfully!!!')


if __name__ == '__main__':
    dssat = Dssat(r'C:\DSSAT47\ZMytest')
    # dssat('maize', '', 'IB0063,IB0060', 'PIO X304C,H610(UH)', 'IBWA8301', '',
    #       'X304C 0 kg N/ha,X304C 50 kg N/ha,X304C 200 kg N/ha', 'H610 0 kg N/ha,H610 50 kg N/ha,H610 200 kg N/ha')
    df = pd.read_excel('input.xlsx', header=0)
    line = df.replace(np.nan, '').values[0, :].tolist()
    dssat(*line)
