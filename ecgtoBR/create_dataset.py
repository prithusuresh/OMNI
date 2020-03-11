import numpy as np
import os
import pandas as pd
import wfdb as wf
from glob import glob
from tqdm import tqdm
from scipy.signal import resample
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from utils import generateSignals,dist_transform
from sklearn.model_selection import train_test_split

import argparse


def main(args):
    path = os.path.join(args.path,"bidmc-ppg-and-respiration-dataset-1.0.0/")
    dat_path = path + '*.dat'
    paths = glob(dat_path)

    paths= sorted([path[:-4] for path in paths if path[-5] != "n"] )

    #GLOBALS
    fs = args.sampling_freq
    fs_upsample = args.upsample_freq
    windowLength = args.window_length #seconds


    ecgSignals = []
    BRSignals = []
    BRAnn1 = []
    BRAnn2 = []

    for path in tqdm(paths):
        
        ann    = wf.rdann(path,'breath')
        samples = np.array(ann.sample)
        aux_note = np.array(ann.aux_note)
        ann1 = samples[(aux_note == "ann1")]
        ann2 = samples[(aux_note == "ann2")]
        record = wf.io.rdrecord(path)
        
        
        ecgSignals.append(record.p_signal[:,record.sig_name.index('II,')])
        BRSignals.append(record.p_signal[:,record.sig_name.index('RESP,')])
        BRAnn1.append(ann1)
        BRAnn2.append(ann2)
    ecgSignals = np.array(ecgSignals,ndmin = 2)
    BRSignals = np.array(BRSignals, ndmin = 2)

    signals = np.stack([ecgSignals,BRSignals], axis= -1 )

        
            
    WINDOWS = 10
    r=0
    inputECG = []
    groundTruth = []

    with tqdm(total = len(signals), desc = "Patient") as pbar:
        for i in range(len(signals)):
                        
            generateSignals = getWindow(signals[i],BRAnn2[i],windows=WINDOWS)

            for sig, ann in generateSignals:
            
                
                ecg = sig[:,0]
                br = sig[:,1]
                
                if len(ecg) == 1 or len(ann) == 0:
                    break


                resampled = resample(ecg, WINDOWS*fs_upsample)
                stdScaler = StandardScaler()
                resampled = stdScaler.fit_transform(resampled.reshape((-1,1)))
                transform = dist_transform(br,ann)
                
                if resampled.shape == (5000,1) and transform.shape == (1250,1):
                    inputECG.append(resampled.reshape((1,-1)))
                    groundTruth.append(transform.reshape((1,-1)))
            pbar.update()


    X_train,X_test,y_train,y_test = train_test_split(np.array(inputECG),np.array(groundTruth),test_size = 0.2, random_state = 42)

    X_train_toTensor = torch.Tensor(X_train).type(torch.float)
    X_test_toTensor = torch.Tensor(X_test).type(torch.float)
    y_train_toTensor = torch.Tensor(y_train).type(torch.float)
    y_test_toTensor = torch.Tensor(y_test).type(torch.float)
    

    torch.save(X_train_toTensor, "data/ecgtoBR_train_data.pt")
    torch.save(y_train_toTensor, "data/ecgtoBR_train_labels.pt")
    torch.save(X_test_toTensor, "data/ecgtoBR_test_data.pt")
    torch.save(y_test_toTensor, "data/ecgtoBR_test_labels.pt")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--sampling_freq',default = 125, type = int, help = 'Sampling Frequency')
    parser.add_argument('--upsample_freq',default = 500, type = int, help = 'Resampling Frequency')
    parser.add_argument('--window_length',default = 5,type = int,help = 'Window Length in seconds')
    parser.add_argument('--path',help = 'Path to unzipped .rar dataset')
    args = parser.parse_args()
    main(args)