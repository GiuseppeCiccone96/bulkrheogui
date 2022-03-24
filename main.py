#Usual imports
import numpy as np
import matplotlib.pyplot as plt
plt.style.use("seaborn-colorblind")
import matplotlib as mpl
mpl.use('qtagg')
import pandas as pd
from pathlib import Path
import os
#Magicclass specific imports
from magicclass import magicclass,set_design,field,set_options,build_help
from magicclass.widgets import Table,CheckBox,PushButton,Figure
from magicgui import magicgui
#Others
from functions import fill_none

#TODO 
#if experiment is either strain sweep or frequency sweep,
#activate buttons for plotting G'/G''. If experiment is stress relaxation
#activate buttons for plottsing shear stress

@magicclass(labels="True",popup_mode="popup",widget_type="split",layout="vertical")
class BulkRheoGUI:
	
	def __init__(self):
		#number of experiments
		self.numexp=0 
		#dataset
		self.dataset=[]
		#files
		self.files=[]

	@magicclass(name="Prepare Experiment",layout="vertical",widget_type="groupbox")
	class PrepareExperiment:

		experiment_toolip = "The experiment type."
		experiment=field(str, options={"label": "Experiment type","choices":["strain sweep",
		"frequency sweep", "stress relaxation"], "tooltip":experiment_toolip})

		def load_file(self,path: Path): ...

		def print_metadata(self): ...

		table_metadata=field(Table)

		# fig_test=field(Figure)

	@PrepareExperiment.wraps
	def load_file(self,path: Path):
		"""Reads rheometer file to extract data of interest."""
		self.path=str(path)
		if self.PrepareExperiment.experiment.value=="strain sweep":
			target_variables = ["Strain","Storage Modulus", "Loss Modulus"]
			skiprows=3
		if self.PrepareExperiment.experiment.value=="frequency sweep":
			target_variables = ["Angular Frequency", "Storage Modulus", "Loss Modulus"]
			skiprows=3
		if self.PrepareExperiment.experiment.value=="stress relaxation":
			target_variables = ["Time","Relaxation Modulus","Shear Stress"] #check stress relaxation files!
			skiprows=2
		with open(self.path, mode='r', encoding='utf-8', errors='ignore') as f:
			self.numexp+=1
			#columns of interest to read and extract 
			reading=False
			magicheader = False 
			databox = []
			data = []
			names=[]
			for riga in f:
				if riga.startswith("Name:"):
					names.append(riga.strip()[8::]) #names of each test
				if reading is False:
					if riga.strip() == "Measuring Profile:": #start reading when we are at "Measuring Profile:"
						reading=True
						if len(data)>0:
							databox.append(data) #np.array(data)
						data = []
						if magicheader is False: #we are at the header
							for _ in range(skiprows): 
								#skipping 3 lines
								f.readline()
							header = f.readline().strip().split('\t')
							#storing index of variables of interest
							headerIndex = []
							for word in target_variables:
								headerIndex.append(header.index(word))
							magicheader = True
							jump = 1 #jump 1 line if we are at header
						else:
							jump = 5 #jump 5 lines if we are at "Measuring Profile:"
						for _ in range(jump):
							#skipping lines
							f.readline()
				else:
					if riga.strip() == "Data Series Information": 
						reading=False
						continue
					else:
						if riga.strip()!='':
							rigaall = np.array((riga.strip().replace(',', '.').split('\t')))
							rigadata = rigaall[headerIndex] #takes only indexes from selected header variables
							newline = list(map(float,rigadata)) #list
							data.append(newline)
			if len(data)>0:
				databox.append(data) #np.array(data)
		self.names=names
		self.data=databox
		self.dataset.append(self.data)
		self.files.append(self.path)
		#self.data[0] is the first "test".
		# converting it to an array allows to have good structure for manipulation, i.e.
		# an array of shape (n_points,n_variables). See target_variables to understand where n_variables
		#comes from.
		# print(np.shape(np.array(self.data))) #shape is not always as expected

	@PrepareExperiment.wraps
	@set_design(text="print metadata")
	def print_metadata(self):
		"""Gets metadata associated with the experiment."""

		metadata = {}
		with open(self.path, mode='r', encoding='utf-8', errors='ignore') as f:
			lines = []
			# First 25 lines
			for _ in range(25):
				lines.append(f.readline().strip())

		# # Number of data points
		# n_points = int(lines[19][lines[19].find(':')+1:].strip())

		# Radius of rheometr tool 
		measuring_system=lines[6][lines[6].find(":")+4:].strip().split('-')
		measuring_tool=measuring_system[0]

		if measuring_tool=="PP25":
			self.tool_radius=25.0/2.0 #mm
		if measuring_tool=="PP15":
			self.tool_radius=15.0/2 #mm
		if measuring_tool=="PP08":
			self.tool_radius=8.0/2 #mm

		# Area of tool
		area = np.pi * self.tool_radius**2 #mm^2
		# Measuring profile
		meas_profile1 = " ".join(lines[23].split())
		meas_profile2 = " ".join(lines[24].split())
		meas_profile = meas_profile1 + "\n" + meas_profile2
		self.metadata = {'Tool Radius [mm]': [self.tool_radius], 'Tool Area [mm^2]': [area], 'Measuring Profile': [meas_profile]}
		self.PrepareExperiment.table_metadata.value=self.metadata

	# plt = field(Figure, options={"nrows": 1, "ncols": 1})
	# plt1 = field(Figure, options={"nrows": 1, "ncols": 1})
	@magicclass(name="Visualization",layout="vertical",widget_type="groupbox")
	class PlotData:
		
		plot_storage_tooltip="Plots storage modulus for each test."
		plot_storage_modulus=field(PushButton,options={"enabled": True,"tooltip":plot_storage_tooltip})
		
		plot_loss_tooltip="Plots loss modulus for each test."
		plot_loss_modulus=field(PushButton,options={"enabled": True,"tooltip":plot_loss_tooltip})

		plot_relax_tooltip="Plots loss modulus for each test (stress relaxation)."
		plot_relax_modulus=field(PushButton,options={"enabled": True,"tooltip":plot_relax_tooltip})

		plot_averages_tooltip="Plots average storage and loss modulus. If tests \n are of different lengths, takes the longest common length for all tests."
		plot_averages=field(False,options={"label":"plot averages","tooltip":plot_averages_tooltip,"visible":True,
		"widget_type":CheckBox})

		table_data_tooltip="Tabulated data for copying and pasting in further software of preference (e.g., Prism)"
		tabledata=field(Table, options={"label": "Experiment type", "tooltip":table_data_tooltip})

	@PlotData.wraps
	@PlotData.plot_averages.connect
	def _plot_averages(self):
		if self.PlotData.plot_averages.value is True:
			#check length of each test 
			#slice data to that length
			#plot average G' and G''
			print("this function does not do anything yet!")
		if self.PlotData.plot_averages.value is False:
			print("why did you click again!")

	@PlotData.wraps
	@PlotData.plot_storage_modulus.connect
	def _plot_storage_modulus(self):
		# self.plt.axes[0].set_yscale('log')
		# self.plt.axes[0].set_xscale('log')
		fig, ax = plt.subplots(1, 1, figsize=(5,5))
		ax.set_yscale('log')
		ax.set_xscale('log')
		fig.suptitle('Storage Modulus')
		ax.set_ylabel('$G^{I}$ (Pa)')
		for i in range(len(self.data)):
			ax.plot(np.array(self.data[i])[:,0], np.array(self.data[i])[:,1],label=self.names[i])
				#set log scale
				# self.plt.axes[0].plot(self.data['strain [%]'][i], self.data['storage modulus [Pa]'][i], '-s')
				# self.plt.axes[0].set_xlabel("Strain (%)")
				# self.plt.axes[0].set_ylabel("$G^{I}$ (Pa)")
				# self.plt.draw()
		plt.legend()
		if self.PrepareExperiment.experiment.value == "strain sweep":
			ax.set_xlabel("Strain (%)")
			plt.show()
		if self.PrepareExperiment.experiment.value == "frequency sweep":
			ax.set_xlabel("Frequency (rad/s)")
			plt.show()
	
	@PlotData.wraps
	@PlotData.plot_loss_modulus.connect
	def _plot_loss_modulus(self):
		#add filename on plot
		# self.plt1.axes[0].set_yscale('log')
		# self.plt1.axes[0].set_xscale('log')
		fig, ax1 = plt.subplots(1, 1, figsize=(5,5))
		ax1.set_yscale('log')
		ax1.set_xscale('log')
		fig.suptitle('Loss Modulus')
		ax1.set_ylabel('$G^{II}$ (Pa)')
		for i in range(len(self.data)):
			ax1.plot(np.array(self.data[i])[:,0], np.array(self.data[i])[:,2],label=self.names[i])
				#set log scale
				# self.plt1.axes[0].plot(self.data['strain [%]'][i], self.data['loss modulus [Pa]'][i], '-o')
				# self.plt1.axes[0].set_xlabel("Strain (%)")
				# self.plt1.axes[0].set_ylabel("$G^{II}$ (Pa)")
				# self.plt1.draw()
		plt.legend()
		if self.PrepareExperiment.experiment.value == "strain sweep":
			ax1.set_xlabel("Strain (%)")
			plt.show()
		if self.PrepareExperiment.experiment.value == "frequency sweep":
			ax1.set_xlabel("Frequency (rad/s)")
			plt.show()

	@PlotData.wraps
	@PlotData.plot_relax_modulus.connect
	def _plot_relax_modulus(self):
		#add filename on plot
		# self.plt1.axes[0].set_yscale('log')
		# self.plt1.axes[0].set_xscale('log')
		fig, ax2 = plt.subplots(1, 1, figsize=(5,5))
		ax2.set_yscale('log')
		ax2.set_xscale('log')
		fig.suptitle('Relaxation Modulus')
		ax2.set_ylabel('$G(t)$ (Pa)')
		ax2.set_xlabel('t (s)')
		for i in range(len(self.data)):
			ax2.plot(np.array(self.data[i])[:,0], np.array(self.data[i])[:,2],label=self.names[i])
		plt.legend()
		plt.show()
	
	@PlotData.wraps
	def tabulate_data(self):
		data=self.data 
		names = np.array(self.names)
	
		if self.PrepareExperiment.experiment.value=="strain sweep":
			variables_names=["Strain","Storage Modulus","Loss Modulus"]

		if self.PrepareExperiment.experiment.value=="frequency sweep":
			variables_names=["Frequency","Storage Modulus","Loss Modulus"]

		if self.PrepareExperiment.experiment.value=="stress relaxation":
			variables_names=["Time","Relaxation Modulus","Shear Stress"]
		
		data = fill_none(data,variables_names)
		
		column_names = variables_names*len(data) #repeat variables names for each test
		new_names = [names[i] for i in range(len(data)) for j in range(len(variables_names))] #repeated names
		datat = np.array([np.array(data[i])[:,j] for i in range(len(data)) for j in range(len(variables_names))]).T
		
		df=pd.DataFrame(datat,columns=[column_names[i]+" "+ new_names[i] for i in range(len(column_names))])
		self.PlotData.tabledata.value=df

	def show_help(self):
		"""Shows help in navigating the gui."""
		build_help(self).show()

if __name__ == "__main__":
	ui = BulkRheoGUI()
	ui.show()
