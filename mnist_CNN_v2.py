# Peter Duggins, psipeter@gmail.com
# SYDE 552/750
# Final Project
# Winter 2016
# CNN Adapted from https://github.com/fchollet/keras/issues/762

# from __future__ import absolute_import
from __future__ import print_function
import numpy as np
import theano
import json
from json_tricks.np import dump, dumps, load, loads, strip_comments
import csv

# Theano configuration
# theano.config.floatX = 'float32'
# theano.config.device = 'gpu'
# import theano.sandbox.cuda
# theano.sandbox.cuda.use("gpu")
# ssh ctnuser@ctngpu2.uwaterloo.ca -p 3656
# pswd neuro...with replacements eio

# Keras imports
from keras.datasets import mnist
from keras.models import Graph
from keras.layers.core import *
from keras.layers.convolutional import *
from keras.optimizers import SGD, Adadelta, Adagrad
from keras.utils import np_utils, generic_utils

# Hyperparameters
filename='mnist_CNN_v2_all_epochs=20'
batch_size = 128
classes = 10
learning_rate=0.01
decay=1e-6
momentum=0.9
nesterov=True
ps=1
frac=1
epochs = 20

# MNIST data
(X_train, y_train), (X_test, y_test) = mnist.load_data()
img_x, img_y = 28,28
X_train = X_train.reshape(X_train.shape[0], 1, img_x, img_y)
X_test = X_test.reshape(X_test.shape[0], 1, img_x, img_y)
X_train = X_train.astype('float32')
X_test = X_test.astype('float32')
X_train /= 255
X_test /= 255
samples_train = frac*X_train.shape[0]
samples_test = frac*X_test.shape[0]
image_dim=(1,img_x,img_y)

# Training parameters
train_datapoints=samples_train
test_datapoints=samples_test
Y_train = np_utils.to_categorical(y_train, classes)
Y_test = np_utils.to_categorical(y_test, classes)


'''
Network
'''
model = Graph()
#input
model.add_input(name='input', input_shape=image_dim)
#1st conv layer
FM1=32
k1=3
ps1=1
s1=int(np.ceil(img_x/ps1)-k1+1)
model.add_node(Convolution2D(FM1, k1, k1, activation='relu'),name='conv0', input='input')
model.add_node(MaxPooling2D(pool_size=(ps, ps)),name='maxpool0', input='conv0')
model.add_node(AveragePooling2D(pool_size=(s1,s1)),name='sal_f0', input='conv0')
model.add_node(Flatten(),name='flat_sal_f0', input='sal_f0')
#2nd conv layer
FM2=32
k2=3
ps2=1
s2=int(np.ceil(s1/ps2)-k2+1)
model.add_node(Convolution2D(FM2, k2, k2, activation='relu'),name='conv1', input='maxpool0')
model.add_node(MaxPooling2D(pool_size=(ps, ps)),name='maxpool1', input='conv1')
model.add_node(AveragePooling2D(pool_size=(s2, s2)),name='sal_f1', input='conv0')
model.add_node(Flatten(),name='flat_sal_f1', input='sal_f1')
#1st to 2nd layer Saliency connection
model.add_node(Dense(FM2,activation='relu'),name='sal_FB_12',
							inputs=['flat_sal_f0','flat_sal_f1'],merge_mode='sum')
#flatten layer
model.add_node(Flatten(),name='flatten', input='maxpool1')
model.add_node(Flatten(),name='flat_sal_FB_12', input='sal_FB_12')
#1st dense layer
model.add_node(Dense(128, activation='relu'),name='dense0', input='flatten')
model.add_node(Dense(FM2, activation='relu'),name='denseS0', input='flat_sal_FB_12')
#2d dense layer
model.add_node(Dense(classes, activation='softmax'),name='dense1', input='dense0')
model.add_node(Dense(classes, activation='softmax'),name='denseS1', input='denseS0')
# output
model.add_output(name='output', inputs=['dense1','denseS1'],merge_mode='sum')





'''optimize, compile, and train'''
sgd = SGD(lr=learning_rate, decay=decay, momentum=momentum, nesterov=nesterov)
model.compile(sgd, {'output':'categorical_crossentropy'})
history=model.fit({'input':X_train[:train_datapoints], 'output':Y_train[:train_datapoints]},
			batch_size=batch_size, nb_epoch=epochs, shuffle=True,
            validation_data={'input':X_test[:test_datapoints], 'output':Y_test[:test_datapoints]})

#TODO automate this with model, weight information (gave up after 3 hrs and no Keras.usergroups response)
arch_dict=OrderedDict((
	('input',			{'type':'input', 			'input_name':'image', 							'weights':None, 									'biases':None, 										'activation':None 																}),
	('conv0', 			{'type':'Convolution2D', 	'input_name':'input', 							'weights':model.nodes['conv0'].get_weights()[0],	'biases':model.nodes['conv0'].get_weights()[1],		'activation':'relu', 	'stride':1, 											}),
	('maxpool0', 		{'type':'MaxPooling2D', 	'input_name':'conv0', 							'weights':None, 									'biases':None,										'activation':None, 		'stride':1, 	'pool_type':'max', 	'pool_size': ps1	}),
	('sal_f0', 			{'type':'AveragePooling2D', 'input_name':'conv0', 							'weights':None, 									'biases':None,										'activation':None, 		'stride':1, 	'pool_type':'avg', 	'pool_size': s1		}),
	('flat_sal_f0',		{'type':'Flatten', 			'input_name':'sal_f0', 							'weights':None,										'biases':None,										'activation':None,  	'stride':1, 											}),
	('conv1', 			{'type':'Convolution2D', 	'input_name':'maxpool0', 						'weights':model.nodes['conv1'].get_weights()[0], 	'biases':model.nodes['conv1'].get_weights()[1], 	'activation':'relu', 	'stride':1, 											}),
	('maxpool1',		{'type':'MaxPooling2D', 	'input_name':'conv1', 							'weights':None,										'biases':None,										'activation':None, 		'stride':1, 	'pool_type':'max', 	'pool_size': ps1	}),
	('sal_f1', 			{'type':'AveragePooling2D', 'input_name':'conv1', 							'weights':None, 									'biases':None,										'activation':None, 		'stride':1, 	'pool_type':'avg', 	'pool_size': s2		}),
	('flat_sal_f1', 	{'type':'Flatten', 			'input_name':'sal_f1', 							'weights':None,										'biases':None,										'activation':None,  	'stride':1, 											}),
	('sal_FB_12', 		{'type':'DenseFB', 			'input_name':['flat_sal_f0','flat_sal_f1'], 	'weights':model.nodes['sal_FB_12'].get_weights()[0],'biases':model.nodes['sal_FB_12'].get_weights()[1],	'activation':'relu',	'stride':1, 											}),
	('flatten', 		{'type':'Flatten', 			'input_name':'maxpool1', 						'weights':None,										'biases':None,										'activation':None, 		'stride':1, 											}),
	('flat_sal_FB_12', 	{'type':'Flatten', 			'input_name':'sal_FB_12',						'weights':None,										'biases':None,										'activation':None,  	'stride':1, 											}),
	('dense0', 			{'type':'Dense', 			'input_name':'flatten', 						'weights':model.nodes['dense0'].get_weights()[0], 	'biases':model.nodes['dense0'].get_weights()[1],	'activation':'relu',	'stride':1,												}),
	('denseS0', 		{'type':'Dense', 			'input_name':'flat_sal_FB_12', 					'weights':model.nodes['denseS0'].get_weights()[0], 	'biases':model.nodes['denseS0'].get_weights()[1],	'activation':'relu',	'stride':1, 											}),
	('dense1', 			{'type':'Dense', 			'input_name':'dense0', 							'weights':model.nodes['dense1'].get_weights()[0],	'biases':model.nodes['dense1'].get_weights()[1], 	'activation':'softmax', 'stride':1, 											}),
	('denseS1', 		{'type':'Dense', 			'input_name':'denseS0', 						'weights':model.nodes['denseS1'].get_weights()[0],	'biases':model.nodes['denseS1'].get_weights()[1], 	'activation':'softmax', 'stride':1, 											}),
	('output', 			{'type':'output', 			'input_name':['dense1','denseS1'], 				'weights':None, 									'biases':None, 										'activation':None 																}),
))


'''output'''
#save layer statistics
def get_outputs(model, input_name, layer_name, X_batch):
    get_outputs = theano.function([model.inputs[input_name].input],
    				model.nodes[layer_name].get_output(train=False), allow_input_downcast=True)
    my_outputs = get_outputs(X_batch)
    return my_outputs

def get_activities(model):
	conv_nodes=[]
	avg_pool_nodes=[]
	max_pool_nodes=[]
	for the_node in model.nodes:
		if (model.nodes[the_node].get_config()['name']) == 'Convolution2D':
			conv_nodes.append(the_node)
		if (model.nodes[the_node].get_config()['name']) == 'AveragePooling2D':
			avg_pool_nodes.append(the_node)
		if (model.nodes[the_node].get_config()['name']) == 'MaxPooling2D':
			max_pool_nodes.append(the_node)
	return conv_nodes, avg_pool_nodes, max_pool_nodes

def output_stuff(model, history):

	#parameters
	params={ #dictionary
		'filename' : filename,
		'batch_size' : batch_size,
		'classes' : classes,
		'epochs' : epochs,
		'learning_rate' : learning_rate,
		'decay' : decay,
		'momentum' : momentum,
		'nesterov' : nesterov,
		'train_datapoints' : train_datapoints,
		'test_datapoints' : train_datapoints,
		}
	with open(filename+'_params.json', 'w') as fp:
	    json.dump(params, fp)

	#architecture, for keras and nengo loading respectively
	json_string = model.to_json()
	open(filename+'_model.json', 'w').write(json_string)


	with open(filename+"_arch.json","w") as datafile:
		dump(arch_dict, datafile)

	# weights
	# model.save_weights(filename+'_weights.h5')

	#history
	history_file = open(filename+"_history.txt", "w")
	history_file.write(str(history.history))
	history_file.close()

def output_stats(filename,conv_nodes, avg_pool_nodes, max_pool_nodes):

	stats_file = open(filename+"_stats.csv", 'w')
	writer = csv.writer(stats_file, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
	row1=['Statistics for %s' %filename]
	writer.writerow(row1)

	for i in range(len(conv_nodes)):
		# Activations are 4-D tensors with (test_datapoints, n_filters_i,shapex,shapey)
		A_conv_raw = get_outputs(model,'input',conv_nodes[i],X_test[:test_datapoints])
		# A_avg_raw = get_outputs(model,'input',avg_pool_nodes[i],X_test[:test_datapoints])
		A_max_raw = get_outputs(model,'input',max_pool_nodes[i],X_test[:test_datapoints])
		# Average over test_datapoints to make a 3-D tensor (n_filters_i,shapex,shapey)
		A_conv = np.average(A_conv_raw,axis=0)
		# A_avg = np.average(A_avg_raw,axis=0)
		A_max = np.average(A_max_raw,axis=0)
		#stats of all conv node activations in layer_i
		mean_A_conv=np.average(A_conv, axis=(0,1,2))
		std_A_conv=np.std(A_conv, axis=(0,1,2))
		max_A_conv=np.max(A_conv, axis=(0,1,2))
		#mean and std for each feature_maps in that layer
		features_mean_A_conv=np.average(A_conv,axis=(1,2))
		features_max_A_conv=np.max(A_conv,axis=(1,2))
		#std of feature map 0 means/maxs across inputs
		trials_mean_A_conv=np.average(A_conv_raw,axis=(2,3))
		trials_max_A_conv=np.max(A_conv_raw,axis=(2,3))
		std_mean_across_trials=np.std(trials_mean_A_conv,axis=0)
		std_max_across_trials=np.std(trials_max_A_conv,axis=0)

		# Write to CSV file
		writer.writerow([])
		writer.writerow(['layer',i])
		writer.writerow(['mean(A) across layer ',mean_A_conv])
		writer.writerow(['std(A) across layer ',std_A_conv])
		writer.writerow(['max(A) across layer ',max_A_conv])
		writer.writerow(['mean(A across trials) for each feature ',[m for m in features_mean_A_conv]])
		writer.writerow(['max(A across trials) for each feature ',[m for m in features_max_A_conv]])
		writer.writerow(['mean(feature map 0) for each trial ',[m[0] for m in trials_mean_A_conv]])
		writer.writerow(['max(feature map 0) for each trial ',[m[0] for m in trials_max_A_conv]])
		writer.writerow(['std (mean(feature map)) across trials ',std_mean_across_trials])
		writer.writerow(['std (max(feature map)) across trials ',std_max_across_trials])
		# writer.writerow(['mean(avg pool unit across trials) within feature map 0 ',[m[0] for m in A_avg[0]]])
		writer.writerow(['mean(max pool unit across trials) within feature map 0 ',[m[0] for m in A_max[0]]])

	stats_file.close()

output_stuff(model, history)
conv_nodes, avg_pool_nodes, max_pool_nodes = get_activities(model)
output_stats(filename,conv_nodes, avg_pool_nodes, max_pool_nodes)

output1 = get_outputs(model,'input','dense1',X_train[:train_datapoints])
output2 = get_outputs(model,'input','denseS1',X_train[:train_datapoints])
guesses = np.argmax(output1+output2, axis=1)
answers = y_train[:train_datapoints]
error_rate=np.count_nonzero(guesses != answers)/float(len(answers))
print ('total error rate',error_rate)
# print (model.nodes['sal_FB_12'].get_weights())
# print ([get_outputs(model,'input',the_node,X_test[:test_datapoints]).shape for the_node in model.nodes])
