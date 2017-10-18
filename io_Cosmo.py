import numpy as np
import tensorflow as tf
import hyper_parameters_Cosmo
import os
from data_aug import *

def _float64_feature(value):
  return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))

def _bytes_feature(value):
  return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


class loadNpyData:
    def __init__(self,data,label,num):
        self.data = data
        self.label = label
        self.num = num
    
    def convert_to(self):
        filename = str(self.num)+'.tfrecord'
        print('Writing ', filename)
        writer = tf.python_io.TFRecordWriter(filename)
        for index in range(len(self.data)):
            data_raw = self.data[index].tostring()
            label_raw = self.label[index].tostring()
            example = tf.train.Example(features = tf.train.Features(feature={'label_raw': _bytes_feature(label_raw),'data_raw': _bytes_feature(data_raw)}))
            writer.write(example.SerializeToString())
        writer.close()

class loadTfrecordData:
    def __init__(self,fileBuffer,num):
        self.fileBuffer = fileBuffer
    
    
    def reconstruct_from(self):
        for filename in record_iterator:
            example = tf.train.Example()
            example.ParseFromString(filename)
            data_raw = (example.features.feature['data_raw'].bytes_list.value[0])
            data = np.fromstring(data_raw, dtype=np.float).reshape([-1,64,64,64,1])
            label_raw = (example.features.feature['label_raw'].bytes_list.value[0])
            label = np.fromstring(label_raw,dtype=np.float).reshape([-1,2])
        return data,label

def read_tfrecord(filename_queue):
    reader = tf.TFRecordReader()    
    _,single_example = reader.read(filename_queue)
    parsed_example = tf.parse_single_example(
    single_example,
    features = {
        "data_raw": tf.FixedLenFeature([],tf.string),
        "label_raw": tf.FixedLenFeature([],tf.string)
    }
    )
    
    NbodySimuDecode = tf.decode_raw(parsed_example['data_raw'],tf.float64)
    labelDecode = tf.decode_raw(parsed_example['label_raw'],tf.float64)
    NbodySimus = tf.reshape(NbodySimuDecode,[64,64,64])
     
    #augment 
    NbodySimus = tf.cond(tf.random_uniform([1],maxval=1)[0] < tf.constant(.5),lambda:NbodySimus,lambda:NbodySimus[::-1,:,...])
    NbodySimus = tf.cond(tf.random_uniform([1],maxval=1)[0] < tf.constant(.5),lambda:NbodySimus,lambda:NbodySimus[:,::-1,...])
    NbodySimus = tf.cond(tf.random_uniform([1],maxval=1)[0] < tf.constant(.5),lambda:NbodySimus,lambda:NbodySimus[:,:,::-1])
    
    prand = tf.random_uniform([1],maxval=1)[0]
    NbodySimus = tf.cond(prand < tf.constant(1./6),lambda:tf.transpose(NbodySimus, perm = (1,2,0)),lambda:NbodySimus)
    NbodySimus = tf.cond(tf.logical_and(prand < tf.constant(2./6) , prand > tf.constant(1./6)), lambda:tf.transpose(NbodySimus, perm = (1,0,2)),lambda:NbodySimus)
    NbodySimus = tf.cond(tf.logical_and(prand < tf.constant(3./6) , prand > tf.constant(2./6)), lambda:tf.transpose(NbodySimus, perm = (0,2,1)),lambda:NbodySimus)
    NbodySimus = tf.cond(tf.logical_and(prand < tf.constant(4./6) , prand > tf.constant(3./6)), lambda:tf.transpose(NbodySimus, perm = (2,0,1)),lambda:NbodySimus)
    NbodySimus = tf.cond(tf.logical_and(prand < tf.constant(5./6) , prand > tf.constant(4./6)), lambda:tf.transpose(NbodySimus, perm = (2,1,0)),lambda:NbodySimus)
    
    #normalize
    NbodySimus /= (tf.reduce_sum(NbodySimus)/64**3+0.)
    NbodySimuAddDim = tf.expand_dims(NbodySimus,axis = 3)
    label = tf.reshape(labelDecode,[2])
    label = (label - tf.constant([2.995679839999998983e-01,8.610806619999996636e-01],dtype = tf.float64))/tf.constant([2.905168635566176411e-02,4.023372385668218254e-02],dtype = tf.float64)
    return NbodySimuAddDim,label
    
def readDataSet(filenames):
    filename_queue = tf.train.string_input_producer(filenames,num_epochs=None,shuffle=True)
    #NbodySimus,label= read_tfrecord(filename_queue)
    NbodyList = [read_tfrecord(filename_queue) for _ in range(hyper_parameters_Cosmo.Input["NUM_THREADS"])]
    NbodySimus_batch, label_batch = tf.train.shuffle_batch_join(
    	#[NbodySimus,label],
	NbodyList,
    	batch_size = hyper_parameters_Cosmo.Input["BATCH_SIZE"],
    	#num_threads = hyper_parameters_Cosmo.Input["NUM_THREADS"],
    	capacity = hyper_parameters_Cosmo.Input["CAPACITY"],
    	min_after_dequeue = hyper_parameters_Cosmo.Input["MIN_AFTER_DEQUEUE"],
	allow_smaller_final_batch=True)
    
    return  NbodySimus_batch, label_batch
    
    
        

if __name__ == '__main__':
    order = np.split(np.random.permutation(64*499),499)
    
    label_path = os.path.join('/zfsauton/home/siyuh/256_64','basics_infos_1000_1499.txt')
    labels = np.loadtxt(label_path,delimiter=',')    
    '''
    for i in range(0,499):
        data = []
        label = []
        for j in order[i]:
            numDirectory = int(j/64)
            numFile = j%64
            data_path = os.path.join('/zfsauton/home/siyuh/256_64',str('01')+str(numDirectory).rjust(3,'0'),str(numFile)+'.npy')
            data = np.append(data,np.load(data_path))
            label = np.append(label,labels[numDirectory][[1,3]])
        loadNpyData(data.reshape(-1,64,64,64,1),label.reshape(-1,2),i).convert_to()
    '''
    NbodySimu, NbodyLabel,prand = readDataSet(filenames=["0.tfrecord"])
    with tf.Session() as sess:
	sess.run(tf.global_variables_initializer())
        coord = tf.train.Coordinator();
        threads = tf.train.start_queue_runners(coord=coord);
        for i in range(10):
            _NbodySimu,_NbodyLabel = sess.run([NbodySimu, NbodyLabel]);
            print _prand
            print ("----------------");
	
	coord.request_stop()
	coord.join()
    
    
    





