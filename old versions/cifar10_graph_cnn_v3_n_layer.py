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

# Theano configuration
# theano.config.floatX = 'float32'
# theano.config.device = 'gpu'
# import theano.sandbox.cuda
# theano.sandbox.cuda.use("gpu")

# Keras imports
from keras.datasets import cifar10
from keras.models import Graph
from keras.layers.core import *
from keras.layers.convolutional import *
from keras.optimizers import SGD, Adadelta, Adagrad
from keras.utils import np_utils, generic_utils

# CIFAR-10 data
(X_train, y_train), (X_test, y_test) = cifar10.load_data()
shapex, shapey, shapez = X_train.shape[2], X_train.shape[3], X_train.shape[1]
samples_train = X_train.shape[0]
samples_test = X_test.shape[0]
image_dim=(shapez,shapex,shapey)

# Parameters
filename='cifar10_graph_cnn_v3_n_layer=10'
batch_size = 32
classes = 10
epochs = 3
learning_rate=0.01
decay=1e-6
momentum=0.9
nesterov=True
train_datapoints=50 #samples_train
test_datapoints=30 #samples_test
n_conv_layers=5
n_dense_layers=3
n_filters = np.arange(16,2*n_conv_layers+16,2) # number of convolutional filters to use at layer_i
pool_size = np.full(shape=n_conv_layers,fill_value=3) # square size of pooling window at layer_i
kernel_size = np.arange(1,2*n_conv_layers,2)[::-1] # square size of kernel at layer_i
dropout_frac = np.full(shape=n_conv_layers+n_dense_layers,fill_value=0.5)# dropout fraction at layer_i
dense_size = np.full(shape=n_dense_layers,fill_value=512) # output dimension for dense layers
params={ #dictionary
	'batch_size' : batch_size,
	'classes' : classes,
	'epochs' : epochs,
	'learning_rate' : learning_rate,
	'decay' : decay,
	'momentum' : momentum,
	'nesterov' : nesterov,
	'n_filters' : n_filters,
	'pool_size' : pool_size,
	'kernel_size' : kernel_size,
	'dropout_frac' : dropout_frac,
	'dense_size' : dense_size,
	'train_datapoints' : train_datapoints, #samples_train
	'test_datapoints' : train_datapoints, #samples_test
	'filename' : filename,
	'n_conv_layers' : n_conv_layers,
	'n_dense_layers' : n_dense_layers,
}

# Convert class vectors to binary class matrices
Y_train = np_utils.to_categorical(y_train, classes)
Y_test = np_utils.to_categorical(y_test, classes)
X_train = X_train.astype('float32')
X_test = X_test.astype('float32')
X_train /= 255
X_test /= 255






'''Network
# In this version, average and max pooling are dead ends at each layer;
# they only calculate statistics'''
model = Graph()

#input and 1st conv layer
model.add_input(name='input', input_shape=image_dim)
model.add_node(Convolution2D(n_filters[0], kernel_size[0], kernel_size[0], 
				activation='relu', input_shape=image_dim),
				name='conv%s' %0, input='input')
model.add_node(AveragePooling2D(pool_size=(pool_size[0], pool_size[0])), 
				name='avgpool%s' %0, input='conv%s' %0)
model.add_node(MaxPooling2D(pool_size=(pool_size[0], pool_size[0])),
				name='maxpool%s' %0, input='conv%s' %0)
model.add_node(Dropout(dropout_frac[0]),
				name='drop%s' %0, input='conv%s' %0)

#conv layers
for i in np.arange(1,n_conv_layers):

	model.add_node(Convolution2D(n_filters[i], kernel_size[i], kernel_size[i], 
					activation='relu', input_shape=image_dim),
					name='conv%s' %i, input='conv%s' %(i-1))
	model.add_node(AveragePooling2D(pool_size=(pool_size[i], pool_size[i])), 
					name='avgpool%s' %i, input='conv%s' %i)
	model.add_node(MaxPooling2D(pool_size=(pool_size[i], pool_size[i])),
					name='maxpool%s' %i, input='conv%s' %i)
	model.add_node(Dropout(dropout_frac[i]),
					name='drop%s' %i, input='conv%s' %i)

#1st dense layer
model.add_node(Flatten(),
				name='flatten', input='conv%s' %(n_conv_layers-1))
model.add_node(Dense(dense_size[0],
				activation='relu', init='glorot_uniform'),
				name='dense%s' %0, input='flatten')

#dense layers
for j in np.arange(1,n_dense_layers):
	model.add_node(Dense(dense_size[j],
					activation='relu', init='glorot_uniform'),
					name='dense%s' %j, input='dense%s' %(j-1))
	model.add_node(Dropout(dropout_frac[j]),
					name='drop%s' %(i+j), input='dense%s' %j)

#classifier layer and output
model.add_node(Dense(classes,
				activation='softmax', init='glorot_uniform'),
				name='dense_output', input='drop%s' %(n_dense_layers+n_conv_layers-2))
model.add_output(name='output', input='dense_output', merge_mode='sum')







'''optimize, compile, and print'''
sgd = SGD(lr=learning_rate, decay=decay, momentum=momentum, nesterov=nesterov)
model.compile(sgd, {'output':'categorical_crossentropy'})

#train
history=model.fit({'input':X_train[:train_datapoints], 'output':Y_train[:train_datapoints]},
			batch_size=batch_size, nb_epoch=epochs, shuffle=True,
            validation_data={'input':X_test[:test_datapoints], 'output':Y_test[:test_datapoints]})
predictions = model.predict({'input':X_test[:test_datapoints]})







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

def output_stuff(params, model, history):

	#parameters
	with open(filename+'_params.json', 'w') as fp:
	    json.dump(params, fp)

	#architecture
	json_string = model.to_json()
	open(filename+'_model', 'w').write(json_string)

	#weights
	model.save_weights(filename+'_weights.h5')

	#history
	history_file = open(filename+"_history.txt", "w")
	history_file.write(history)
	history_file.close()

def output_stats(filename,conv_nodes, avg_pool_nodes, max_pool_nodes):

	stats_file = open(filename+"_stats.txt", "w")

	id_string="Layer #\n\
	within all feature maps: mean(A) \t std(A) \t min(A) \t max(A)\n\
	across all feature maps: std(mean) \t std(max)\n\
	within avg pooled feature[0]: mean(mean(A_subset)) \t std(mean(A_subset)) \t min(mean(A_subset)) \t max(mean(A_subset))\n\
	across avg pooled feature[0]: std(mean(mean(A_subset))) \t std(max(mean(A_subset)))\n\
	within max pooled feature[0]: mean(max(A_subset)) \t std(max(A_subset)) \t min(max(A_subset)) \t max(max(A_subset))\n\
	across max pooled feature[0]: std(mean(max(A_subset))) \t std(max(max(A_subset)))\n"
	print (id_string)
	stats_file.write(id_string)

	for i in range(len(conv_nodes)):
		A_conv = get_outputs(model,'input',conv_nodes[i],X_test[:test_datapoints])
		A_avg = get_outputs(model,'input',avg_pool_nodes[i],X_test[:test_datapoints])
		A_max = get_outputs(model,'input',max_pool_nodes[i],X_test[:test_datapoints])

		layer=str(i)
		print ('\n'+layer+'\n')
		stats_file.write('\n'+layer+'\n')

		mean_A_conv=str(np.average(A_conv))
		std_A_conv=str(np.std(A_conv))
		min_A_conv=str(np.min(A_conv))
		max_A_conv=str(np.max(A_conv))
		std_across_mean_A_conv=str(np.std(np.average(A_conv,axis=(0,2,3))))
		std_across_max_A_conv=str(np.std(np.max(A_conv,axis=(0,2,3))))
		string1=mean_A_conv+'\t'+std_A_conv+'\t'+min_A_conv+'\t'+max_A_conv+'\n'
		string2=std_across_mean_A_conv+'\t'+std_across_max_A_conv+'\n'
		print (string1,string2)
		stats_file.write(string1)
		stats_file.write(string2)

		mean_A_avg=str(np.average(A_avg[:,0]))
		std_A_avg=str(np.std(A_avg[:,0]))
		min_A_avg=str(np.min(A_avg[:,0]))
		max_A_avg=str(np.max(A_avg[:,0]))
		std_across_mean_A_avg=str(np.std(np.average(A_avg[:,0],axis=0)))
		std_across_max_A_avg=str(np.std(np.max(A_avg[:,0],axis=0)))
		string1=mean_A_avg+'\t'+std_A_avg+'\t'+min_A_avg+'\t'+max_A_avg+'\n'
		string2=std_across_mean_A_avg+'\t'+std_across_max_A_avg+'\n'
		print (string1,string2)
		stats_file.write(string1)
		stats_file.write(string2)

		mean_A_max=str(np.average(A_max[:,0]))
		std_A_max=str(np.std(A_max[:,0]))
		min_A_max=str(np.min(A_max[:,0]))
		max_A_max=str(np.max(A_max[:,0]))
		std_across_mean_A_max=str(np.std(np.average(A_max[:,0],axis=0)))
		std_across_max_A_max=str(np.std(np.max(A_max[:,0],axis=0)))
		string1=mean_A_max+'\t'+std_A_max+'\t'+min_A_max+'\t'+max_A_max+'\n'
		string2=std_across_mean_A_max+'\t'+std_across_max_A_max+'\n'
		print (string1,string2)
		stats_file.write(string1)
		stats_file.write(string2)

	stats_file.close()

output_stuff(params, model, str(history))
conv_nodes, avg_pool_nodes, max_pool_nodes = get_activities(model)
output_stats(filename,conv_nodes, avg_pool_nodes, max_pool_nodes)