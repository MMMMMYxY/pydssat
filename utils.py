import pandas as pd
import json
import numpy as np
import os
import datetime


def create_input_files(in_path, out_path):
    """
    Create an reorganized json file of original input data.
    The json file is the summary of data.
        xfile_dict will be a form of
            {crop_types:{file_names:{cultivar:N,cname:NAME,ingenos:ING,treatments:TRM,soil:...}}}
    :param in_path: The path of summary input data.
    :param out_path: The path of reorganized input data.
    :return:None
    """
    # The dict to preserve the reorganized data in the particular form as described in COMMENT
    xfile_dict = {}
    df = pd.read_excel(in_path, header=0, dtype=np.str)

    # Create the basic form of xfile_dict：{crop_types:{file_names:{{ingeno:IDX},{weather:IDX},{soil:IDX}}}}
    # ingeno will be used to search for cultivar_index
    for c in np.unique(df['crop_type']):
        xfile_dict.update({c: {}})
        for f in np.unique(df[df['crop_type'] == c]['file_name']):
            xfile_dict[c].update({f: {}})

            # There are two mean parts in xfile_dict[c][f]:
            #   (1)marked INDIES' LEVEL for the whole file
            #   (2)create a array named 'details' to hold each treatment
            xfile_dict[c][f].update({'details': []})

            df_c = df[df['crop_type'] == c]
            df_c_f = df_c[df_c['file_name'] == f]

            # (2).1 mark CU index with ingeno:
            xfile_dict[c][f].update({'culitvar': {}})
            xfile_dict[c][f].update({'ing-cname': {}})
            for i, ing in enumerate(np.unique(df_c_f['ingeno'])):
                xfile_dict[c][f]['culitvar'].update({ing: i + 1})
                xfile_dict[c][f]['ing-cname'].update(
                    {ing: str(np.unique((df_c_f[df_c_f['ingeno'] == ing])['cname'])[0])})

            # (2).2 FL index associates with weather and soil date which normally unchange in experiment,
            # which means we don't need to mark FL index.

            # (2).3 ML index associates with fertilizer:
            xfile_dict[c][f].update({'fertilizer': {}})
            for i, ft in enumerate(np.unique(df_c_f['FERTILIZERS'])):
                xfile_dict[c][f]['fertilizer'].update({ft: i})

    # Fill the xfile_dict with detail
    for i in range(len(df)):
        df_line = df.iloc[i, :]
        crop = df_line['crop_type']
        fname = df_line['file_name']
        xfile_dict[crop][fname]['details'].append({'ingeno': df_line['ingeno'],
                                                   # 'cname': df_line['cname'],
                                                   'weather': df_line['weather'],
                                                   'soil': df_line['soil'],
                                                   'PDATE': df_line['PDATE'],
                                                   'EDATE': df_line['EDATE'],
                                                   'FERTILIZERS': df_line['FERTILIZERS']})
    # print(xfile_dict)

    with open(os.path.join(out_path, 'xfile.json'), 'w', encoding='utf-8') as j:
        json.dump(xfile_dict, j)


def _create_xfile(out_path, crop_type, file_name, file_dict):
    """
    Create a single xfiles by given particular crop type and file name.
    :param out_path: The directory path to .X file.
    :param crop_type: The crop type.
    :param file_name: File name associate with json file and output .X file.
    :param file_dict: This part is from xfile_dict[c][f].
    :return:
    """
    details_array = file_dict['details']
    suffixes = {'maize': '.MZX', 'rice': '.RIX'}
    abbreviation = {'maize': 'MZ', 'rice': 'RI'}

    # simply consider those params are unchanged
    pdate = details_array[0]['PDATE']
    edate = details_array[0]['EDATE']
    weather = details_array[0]['weather']
    soil = details_array[0]['soil']

    # get STATION param and YEAR param by fname
    year = ''.join(list(filter(str.isnumeric, file_name))[:2])
    now = datetime.datetime.now().year.__str__()[-2:]
    if int(now) >= int(year):
        year = '20' + year
    else:
        year = '19' + year
    station = ''.join(list(filter(str.isalpha, file_name)))

    # use the part of xfile_dict[c][f]'s marked INDIES' LEVEL to fill the lines in xfile
    treatments = ''
    for i, d in enumerate(details_array):
        treatments += '{number:2d} 1 1 0 {cname:<26}{cultivar:2}  1  0  1  1  1  0  1  0  0  0  0  1\n'.format(
            number=i + 1, cname=file_dict['ing-cname'][d['ingeno']], cultivar=file_dict['culitvar'][d['ingeno']]
        )
    cultivars = ''
    for ing, idx in file_dict['culitvar'].items():
        cultivars += '{cultivar:2d} {abbreviation} {ingeno} {cname}\n'.format(
            cultivar=idx, abbreviation=abbreviation[crop_type], ingeno=ing, cname=file_dict['ing-cname'][ing]
        )
    fertilizer = ''
    for fts, idx in file_dict['fertilizer'].items():
        for ft in fts.split(';'):
            fertilizer += '{0:2d} {1:5}{2:>6}{3:>6}{4:>6}{5:>6}{6:>6}{7:>6}   -99   -99   -99 -99\n'.format(
                int(idx), *(ft.strip().split(' '))
            )

    base_file = '''
*EXP.DETAILS: {file_name}{abbreviation} {station}{year}

*GENERAL
@PEOPLE
-99
@ADDRESS
-99
@SITE
-99

*TREATMENTS                        -------------FACTOR LEVELS------------
@N R O C TNAME.................... CU FL SA IC MP MI MF MR MC MT ME MH SM
{treatments}

*CULTIVARS
@C CR INGENO CNAME
{cultivars}     

*FIELDS
@L ID_FIELD WSTA....  FLSA  FLOB  FLDT  FLDD  FLDS  FLST SLTX  SLDP  ID_SOIL    FLNAME
 1 {station}0001 {weather}   -99   -99   -99   -99   -99   -99 -99    -99  {soil} -99                       
@L ...........XCRD ...........YCRD .....ELEV .............AREA .SLEN .FLWR .SLAS FLHST FHDUR
 1             -99             -99       -99               -99   -99   -99   -99   -99   -99

*SOIL ANALYSIS
@A SADAT  SMHB  SMPX  SMKE  SANAME
 1 {PDATE:5}   -99   -99   -99  -99                     
@A  SABL  SADM  SAOC  SANI SAPHW SAPHB  SAPX  SAKE  SASC
 1    15   -99   -99   -99   -99   -99   -99   -99   -99

*INITIAL CONDITIONS
@C   PCR ICDAT  ICRT  ICND  ICRN  ICRE  ICWD ICRES ICREN ICREP ICRIP ICRID ICNAME              ！2006写06***,2007年写07***，其中***表示播种日期的日序数-1
 1    {abbreviation} {PDATE_minus_1:05d}   -99   -99     1     1   -99   -99   -99   -99   -99   -99 -99
@C  ICBL  SH2O  SNH4  SNO3
 1    25  .394    .4   3.4
 1    55  .428    .4   3.4

*PLANTING DETAILS
@P PDATE EDATE  PPOP  PPOE  PLME  PLDS  PLRS  PLRD  PLDP  PLWT  PAGE  PENV  PLPH  SPRL                        PLNAME     
 1 {PDATE:5} {EDATE:5}     5     4     S     R    60     0     5   -99   -99   -99   -99   -99                        -99


*IRRIGATION AND WATER MANAGEMENT
@I  EFIR  IDEP  ITHR  IEPT  IOFF  IAME  IAMT IRNAME
 1     1    30    50   100 GS000 IR001    10 -99
@I IDATE  IROP IRVAL
 1 {PDATE:5}   -99   -99                        

*FERTILIZERS (INORGANIC)
@F FDATE  FMCD  FACD  FDEP  FAMN  FAMP  FAMK  FAMC  FAMO  FOCD FERNAME
{fertilizer}             

*RESIDUES AND ORGANIC FERTILIZER
@R RDATE  RCOD  RAMT  RESN  RESP  RESK  RINP  RDEP  RMET RENAME
 1 {PDATE:5}   -99   -99   -99   -99   -99   -99   -99   -99 -99                          

*CHEMICAL APPLICATIONS
@C CDATE CHCOD CHAMT  CHME CHDEP   CHT..CHNAME
 1 {PDATE:5}   -99   -99   -99   -99   -99  -99                                       

*TILLAGE AND ROTATIONS
@T TDATE TIMPL  TDEP TNAME
 1 {PDATE:5}   -99   -99 -99                                                              

*ENVIRONMENT MODIFICATIONS
@E ODATE EDAY  ERAD  EMAX  EMIN  ERAIN ECO2  EDEW  EWIND ENVNAME  
 1 {PDATE:5} A   0 A   0 A   0 A   0 A 0.0 A   0 A   0 A   0                                  

*HARVEST DETAILS
@H HDATE  HSTG  HCOM HSIZE   HPC  HBPC HNAME
 1 {PDATE:5} GS000   -99   -99   -99   -99 Maize                                         

*SIMULATION CONTROLS
@N GENERAL     NYERS NREPS START SDATE RSEED SNAME.................... SMODEL
 1 GE              1     1     S {PDATE:5}  2150 DEFAULT SIMULATION CONTR  MZCER                                 
@N OPTIONS     WATER NITRO SYMBI PHOSP POTAS DISES  CHEM  TILL   CO2
 1 OP              Y     Y     N     N     N     N     N     N     M
@N METHODS     WTHER INCON LIGHT EVAPO INFIL PHOTO HYDRO NSWIT MESOM MESEV MESOL
 1 ME              M     M     E     R     S     C     R     1     G     S     2
@N MANAGEMENT  PLANT IRRIG FERTI RESID HARVS
 1 MA              R     N     R     N     M
@N OUTPUTS     FNAME OVVEW SUMRY FROPT GROUT CAOUT WAOUT NIOUT MIOUT DIOUT VBOSE CHOUT OPOUT FMOPT
 1 OU              N     Y     Y     1     Y     N     N     N     N     N     D     N     Y     A

@  AUTOMATIC MANAGEMENT
@N PLANTING    PFRST PLAST PH2OL PH2OU PH2OD PSTMX PSTMN
 1 PL          {PDATE:5} {PDATE:5}    40   100    30    40    10                    
@N IRRIGATION  IMDEP ITHRL ITHRU IROFF IMETH IRAMT IREFF
 1 IR             30    50   100 GS000 IR001    10     1
@N NITROGEN    NMDEP NMTHR NAMNT NCODE NAOFF
 1 NI             30    50    25 FE001 GS000
@N RESIDUES    RIPCN RTIME RIDEP
 1 RE            100     1    20
@N HARVEST     HFRST HLAST HPCNP HPCNR
 1 HA              0 {PDATE:5}   100     0                                      
    '''.format(file_name=file_name, abbreviation=abbreviation[crop_type], treatments=treatments,
               cultivars=cultivars, weather=weather, soil=soil, station=station, year=year,
               PDATE=pdate, PDATE_minus_1=int(pdate) - 1, EDATE=edate, fertilizer=fertilizer)
    with open(os.path.join(out_path, file_name + suffixes[crop_type]), 'w', encoding='utf-8') as fp:
        fp.write(base_file)


def create_xfile(in_file, out_path, crop_type=None, file_name=None):
    """
    Create xfiles in a pointed strategy.
    :param in_file: The json file cotain summary data.
    :param out_path: The directory path to .X file.
    :param crop_type:
        None: Create every crop_type from in_file;
        str: Create particular crop_type from in_file.
    :param file_name:
        None: Create every file from in_file;
        list: Create particular file which is in list from in_file
        str: Create particular file from in_file.
    :return:
        1: Unexpected type of file_name
        2: Unexpected type of file_dict
    """
    if not os.path.exists(out_path):
        os.mkdir(out_path)
    with open(in_file, 'r', encoding='utf-8') as j:
        xfile_dict = json.load(j)
    if crop_type is None:
        for c, cdict in xfile_dict.items():
            if file_name is None:
                for fname, fdict in cdict.items():
                    _create_xfile(out_path, c, fname, fdict)
            elif isinstance(file_name, list):
                for fname in file_name:
                    _create_xfile(out_path, c, fname, cdict[fname])
            elif isinstance(file_name, str):
                _create_xfile(out_path, c, file_name, cdict[file_name])
            else:
                print('Unrecognized type of FILE_NAME:%s' % type(file_name))
                return 2
    elif isinstance(crop_type, str):
        c, cdict = crop_type, xfile_dict[crop_type]
        if file_name is None:
            for fname, fdict in cdict.items():
                _create_xfile(out_path, c, fname, fdict)
        elif isinstance(file_name, list):
            for fname in file_name:
                _create_xfile(out_path, c, fname, cdict[fname])
        elif isinstance(file_name, str):
            _create_xfile(out_path, c, file_name, cdict[file_name])
        else:
            print('Unexpected type of FILE_NAME:%s' % type(file_name))
            return 2
    else:
        print('Unexpected type of CROP_TYPE:%s' % type(crop_type))
        return 1


if __name__ == '__main__':
    # create_input_files('test.xlsx', '.')
    create_xfile('xfile.json', './output',crop_type='maize',file_name='AUAR0601')
