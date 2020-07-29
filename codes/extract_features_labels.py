import sys
import os
import numpy as np
import librosa
import torch
from params import *

#function to create N-frame overlapping chunks of the full audio spectrogram  
def makechunks(x,duration,hop):
        n_chunks=int(np.floor((x.shape[1]-duration)/hop) + 1)
        y=np.zeros([n_chunks,x.shape[0],duration])
        for i in range(n_chunks):
                y[i]=x[:,i*hop:(i*hop)+duration]
		#normalise
                y[i]=(y[i]-np.min(y[i]))/(np.max(y[i])-np.min(y[i]))
        return y

#data dirs
audio_dir=sys.argv[1]	#containing audios of all the sections and their time-scaled versions
save_dir=sys.argv[2]		#output directory to save features and labels

#set of hop values and time-scaling factors for each s.t.m. to balance data
mode=sys.argv[3] #'voc', 'pakh', 'net'

if mode=='voc':
    input_hops_stm={1.:int(np.floor(1./(hopsize/fs))), 2.:int(np.floor(0.5/(hopsize/fs))), 4.:int(np.floor(0.5/(hopsize/fs))), 8.:int(np.floor(0.1/(hopsize/fs)))}
    aug_ts_versions={1.:[0.8,0.92,1.0,1.12],2.:[0.8,0.92,1.0,1.12],4.:[0.8,0.92,1.0,1.12],8.:[0.8,0.84,0.88,0.92,0.96,1.0,1.04,1.08,1.12,1.16]}

elif mode=='pakh':
    input_hops_stm={1.:int(np.floor(0.5/(hopsize/fs))), 2.:int(np.floor(0.5/(hopsize/fs))), 4.:int(np.floor(1./(hopsize/fs))), 8.:int(np.floor(1./(hopsize/fs))), 16.:int(np.floor(0.5/(hopsize/fs)))}
    aug_ts_versions={1.:[0.8,0.84,0.92,0.96,1.0,1.04,1.12,1.16],2.:[0.8,0.84,0.92,0.96,1.0,1.04,1.12,1.16],4.:[0.8,0.92,1.0,1.12],8.:[0.8,0.92,1.0,1.12],16.:[0.8,0.84,0.92,0.96,1.0,1.04,1.12,1.16]}
	
elif mode=='net':
    input_hops_stm={1.:int(np.floor(0.5/(hopsize/fs))), 2.:int(np.floor(0.5/(hopsize/fs))), 4.:int(np.floor(1./(hopsize/fs))), 8.:int(np.floor(1./(hopsize/fs))), 16.:int(np.floor(0.5/(hopsize/fs)))}
    aug_ts_versions={1.:[0.8,0.84,0.92,0.96,1.0,1.04,1.12,1.16],2.:[0.8,0.84,0.92,0.96,1.0,1.04,1.12,1.16],4.:[0.8,0.92,1.0,1.12],8.:[0.8,0.92,1.0,1.12],16.:[0.8,0.84,0.92,0.96,1.0,1.04,1.12,1.16]}

#main
annotations=np.loadtxt('../annotations/section_boundaries_labels.csv',delimiter=',',dtype=str)
songlist=os.listdir(audio_dir)
labels_stm={}

for i,item in enumerate(songlist):
        print("%d/%d audios"%(i+1,len(songlist)))

        section_aug_name=item.replace('.wav','')
        #get section details
        section_name='_'.join([item.split('_')[0],item.split('_')[1],item.split('_')[2],item.split('_')[3]])
        section_name=section_name.replace('.wav','')

        if mode=='voc':
            label_stm=float(annotations[np.where(annotations[:,0]==section_name)[0][0]][3])
        elif mode=='pakh':
            label_stm=float(annotations[np.where(annotations[:,0]==section_name)[0][0]][4])
        elif mode=='net':
            label_stm=float(annotations[np.where(annotations[:,0]==section_name)[0][0]][5])

        #choose required augmented versions
        try: aug_ts=float(section_aug_name.split('_')[5])
        except: aug_ts=1.0
        if (label_stm not in [1.,2.,4.,8.,16.]): continue
        if (aug_ts not in aug_ts_versions[label_stm]): continue

		#choose hop value
        input_hop=input_hops_stm[label_stm]

        #load audio and onsets
        x,fs=librosa.load(os.path.join(audio_dir,item), sr=fs)

        #get log mel spectrogram
        melgram=librosa.feature.melspectrogram(x,sr=fs,n_fft=nfft, hop_length=hopsize, win_length=winsize, n_mels=40, fmin=20, fmax=8000)
        melgram=10*np.log10(1e-10+melgram)

        if melgram.shape[1]<input_len: continue

        #make chunks
        melgram_chunks=makechunks(melgram,input_len,input_hop)

        #save
        savedir=os.path.join(save_dir,section_aug_name)
        if not os.path.exists(savedir): os.makedirs(savedir)

        for i_chunk in range(melgram_chunks.shape[0]):
                savepath=os.path.join(savedir,str(i_chunk)+'.pt')
                torch.save(torch.tensor(np.array(melgram_chunks[i_chunk])).type(torch.float32), savepath)

                #append labels to dict
                labels_stm.update({os.path.join(section_aug_name,str(i_chunk)+'.pt'):label_stm})

np.save(os.path.join(save_dir,'labels_stm.npy'),labels_stm)
