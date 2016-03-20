# Peter Duggins
# SYDE 552/750
# Assignment: Linear-Nonlinear Poisson Models (LNP)
# March 22, 2016

import numpy as np
import matplotlib.pyplot as plt
import scipy.signal
plt.rcParams['lines.linewidth'] = 4
plt.rcParams['font.size'] = 20

#Generate 50 10-second trials of Poisson spikes
#at 25 spikes/s witha 5ms absolute refractory period.
#To do this, draw samples from an approprpiate ISI distribution.
#I'll implement the 5ms refractory period as using dt=5ms.

def generate_poisson_spikes(T,dt,trials,rate,rng):
	
	spike_raster=[]
	spike_times=[]
	for trial in range(trials):
		spike_raster_trial=[]
		spike_times_trial=[]
		for t in range(int(T/dt)):
			spike_here=(rng.rand()<rate*dt)
			spike_raster_trial.append(1*spike_here)
			if spike_here:
				spike_times_trial.append(t*dt)
		spike_raster.append(spike_raster_trial)
		spike_times.append(spike_times_trial)
	return np.array(spike_raster),np.array(spike_times)

def get_ISI(spike_times):

	#calculate across all trials
	ISI=[]
	for trial in range(len(spike_times)):
		for t in range(len(spike_times[trial])-1):
			ISI.append(spike_times[trial][t+1]-spike_times[trial][t])
	return ISI

def get_CV(ISI):

	return np.std(ISI)/np.average(ISI)

def get_fano_factor(spike_raster,t_range):

	count=[np.sum(raster[:t_range]) for raster in spike_raster]
	avg=np.average(count)
	if avg != 0:
		var=np.var(count)
	else:
		var=0
	return var/avg

def get_fano_factor_list(T,dt,trials,rate,rng,n_FFs,t_range):

	FF_list=[]
	for i in range(n_FFs):
		spike_raster, spike_times = generate_poisson_spikes(T,dt,trials,rate,rng)
		FF_i=get_fano_factor(spike_raster,t_range)
		FF_list.append(FF_i)
	return FF_list

def one():

	T=10 #seconds
	dt=0.005
	trials=50
	rate=25 #Hz
	seed=3
	t=np.arange(0,T,dt)
	rng=np.random.RandomState(seed=seed)

	spike_raster, spike_times = generate_poisson_spikes(T,dt,trials,rate,rng)

	ISI = get_ISI(spike_times)
	n_bins=int(np.max(ISI)/(2*dt))

	#Plot the spike raster for first 1.0 seconds
	fig=plt.figure(figsize=(16,16))
	ax=fig.add_subplot(211)
	ax.eventplot(spike_times,colors=[[0,0,0]])
	ax.set_xlim(0,1.0)
	ax.set_ylim(0,trials)
	ax.set_xlabel('time (s)')
	ax.set_ylabel('neuron')

	#plot ISI histogram
	ax=fig.add_subplot(212)
	ax.hist(ISI,n_bins)
	ax.set_xlim(0,dt*100)
	ax.set_xlabel('ISI (s)')
	ax.set_ylabel('frequency')
	plt.show()

	CV = get_CV(ISI)
	print "The coefficient of variation is", CV

	t_range=int(0.100/dt)
	n_FFs = 50

	FF_list_1 = get_fano_factor_list(T,dt,trials,rate,rng,n_FFs,t_range)
	print "Fano Factor for $t_{ref}=%s$, %s trials:" %(dt, n_FFs)
	print "mean: %s" %np.average(FF_list_1), "std: %s" %np.std(FF_list_1)

	dt=0.001
	FF_list_2 = get_fano_factor_list(T,dt,trials,rate,rng,n_FFs,t_range)
	print "Fano Factor for $t_{ref}=%s$, %s trials:" %(dt, n_FFs)
	print "mean: %s" %np.average(FF_list_2), "std: %s" %np.std(FF_list_2)

	#the mean approaches 1 as t_{ref} appoaches 0, but the std increases slightly


def white_noise(mean=0,std=1,T=100,dt=0.001,rng=np.random.RandomState()):
	return rng.normal(mean,std,T/dt)

def synthetic_neuron(drive,rng):
	"""
	Simulates a mock neuron with a time step of 1ms.
	Arguments:
	drive - input to the neuron (expect zero mean; SD=1)
	Returns:
	rho - response function (0=non-spike and 1=spike at each time step)
	"""	
	  
	dt = 0.001
	T = dt*len(drive)
	time = np.arange(0, T, dt)
	lagSteps = 0.02/dt
	drive = np.concatenate((np.zeros(lagSteps), drive[lagSteps:]))
	system = scipy.signal.lti([1], [0.03**2, 2*0.03, 1])
	_, L, _ = scipy.signal.lsim(system, drive[:,np.newaxis], time)
	rate = np.divide(30, 1 + np.exp(50*(0.05-L)))
	spikeProb = rate*dt
	return rng.rand(len(spikeProb)) < spikeProb

def spike_trig_avg(stim,spikes,dt,window_width):

	window = np.arange(0,int(window_width / dt),1)
	#truncate spikes in first window timesteps
	spike_indices=np.where(spikes[len(window):]==1)[0].flatten()
	spike_triggered_avg=[]
	for t in window:
		stim_sum_i=[]
		for i in spike_indices:
			#undo truncation when indexing from stimulus
			stim_sum_i.append(stim[(i+len(window))-t])
		spike_triggered_avg.append(np.average(stim_sum_i))

	spike_triggered_avg=np.array(spike_triggered_avg).flatten()/len(spike_indices)

	return -1.0*window*dt, spike_triggered_avg

def two():

	T=2.0
	dt=0.001
	mean=0
	std=1
	seed=3

	#generate noisy signal with gaussian sampled numbers
	rng=np.random.RandomState(seed=seed)
	noise=white_noise(mean,std,T,dt,rng)
	t=np.arange(0,T,dt)

	#generate colored noise by convolving the noise signal with a gaussian
	sigma=0.020
	G = np.exp(-(t-np.average(t))**2/(2*sigma**2))     
	G = G / sum(G)
	colored_noise=np.convolve(noise,G,'same')

	#feed colored noise into Bryan's spike generator
	spikes=synthetic_neuron(noise,rng)
	smooth_spikes=synthetic_neuron(colored_noise,rng)
	rate=spikes.sum()/T
	smooth_rate=smooth_spikes.sum()/T

	#calculate the spike-triggered average
	window_width=0.100
	window, sta = spike_trig_avg(noise,spikes,dt,window_width)
	smooth_window, smooth_sta = spike_trig_avg(colored_noise,smooth_spikes,dt,window_width)

	# #Plot the spike-triggered average
	# fig=plt.figure(figsize=(16,8))
	# ax=fig.add_subplot(111)
	# ax.plot(smooth_window,smooth_sta)
	# ax.set_xlabel('time (seconds)')
	# ax.set_ylabel('spike-triggered average')
	# plt.show()

	kernel = rate * sta / std**2
	smooth_kernel = smooth_rate * smooth_sta / std**2

	LNP = np.convolve(noise, kernel, mode='same')
	smooth_LNP = np.convolve(colored_noise, smooth_kernel, mode='same')

	#Plot the white noise signal together with the LNP rate prediction
	fig=plt.figure(figsize=(16,16))
	ax=fig.add_subplot(211)
	ax.plot(t,noise,label='white noise signal')
	ax.plot(t,LNP,label='LNP model rate prediction')
	ax.set_xlim(0,T)
	legend=ax.legend(loc='best',shadow=True)
	ax.set_xlabel('time (seconds)')
	ax.set_ylabel('value')

	ax=fig.add_subplot(212)
	ax.plot(t,colored_noise,label='smoothed white noise signal')
	ax.plot(t,smooth_LNP,label='LNP model rate prediction')
	ax.set_xlim(0,T)
	legend=ax.legend(loc='best',shadow=True)
	ax.set_xlabel('time (seconds)')
	ax.set_ylabel('value')
	plt.show()

# one()
two()