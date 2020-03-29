import utils
from dssat import DSSAT
import os
import argparse

SUFFIXES = {'maize': '.MZX', 'rice': '.RIX'}


def run_model(input_summary_file, output_summary_file, out_crop_path, result_output, gl_epochs, crop_type=None,
              file_name=None, run_path_absolute=r'C:\DSSAT47', glue_flag=1, simulation_model='B'):
    utils.create_input_files(input_summary_file, output_summary_file)
    utils.create_xfile(os.path.join(output_summary_file, 'xfile.json'), out_crop_path, crop_type, file_name)
    for fn in os.listdir(out_crop_path):
        if os.path.splitext(fn)[-1] in list(SUFFIXES.values()):
            dssat = DSSAT(os.path.join(out_crop_path, fn), run_path_absolute)
            dssat(result_output, gl_epochs, glue_flag, simulation_model)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Dssat model with GLUE')
    parser.add_argument('--input', '-i', help='path to input summary file')
    parser.add_argument('--output', '-o', default=os.getcwd(),
                        help='path to preserve reorganized summary output file')
    parser.add_argument('--cropdir', '-cd', default=os.path.join(os.getcwd(), 'output'),
                        help='path to preserve reorganized summary output file')
    parser.add_argument('--result', '-rs', default=os.path.join(os.getcwd(), 'result'),
                        help='path to preserve result files of dssat model')
    parser.add_argument('--epochs', '-e', default=5000, help='Epochs of GLUE')

    args = parser.parse_args()

    run_model(args.input, args.output, args.cropdir, args.result, args.epochs)
