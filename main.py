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
from magicclass.widgets import Table,CheckBox,PushButton, Figure
from magicgui import magicgui
#Others
from functions import fill_none
import motor

@magicclass(error_mode="msgbox",labels="True",popup_mode="popup",widget_type="split",layout="vertical")
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

		mode = field(str, options = {"label":" Use mode", "choices":["all data",
		"sample replicates"]}) #idea: if mode is equal to "sample replicates", allow user to average data
		#and create average plot; if mode is equal to "all data", leave gui as it is

		def load_file(self,path: Path): ...

		def print_metadata(self): ...

		table_metadata=field(Table)

	@PrepareExperiment.wraps
	@PrepareExperiment.mode.connect
	def _toggle_mode(self):
		"""Controls the operation mode of the GUI (plotting)"""
		if self.PrepareExperiment.mode.value=="all data":
			self.PlotData.plot_averages.visible=False
		if self.PrepareExperiment.mode.value=="sample replicates":
			self.PlotData.plot_averages.visible=True

	
	@PrepareExperiment.wraps
	@PrepareExperiment.experiment.connect
	def _toggle_experiment(self):
		"""Controls visibility of plotting fields based on experiment type."""
		if self.PrepareExperiment.experiment.value=="stress relaxation":
			self.PlotData.plot_relax_modulus.visible=True
			self.PlotData.plot_storage_modulus.visible=False
			self.PlotData.plot_loss_modulus.visible=False
		elif self.PrepareExperiment.experiment.value=="strain sweep" or  self.PrepareExperiment.experiment.value=="frequency sweep":
			self.PlotData.plot_relax_modulus.visible=False
			self.PlotData.plot_storage_modulus.visible=True
			self.PlotData.plot_loss_modulus.visible=True

	@PrepareExperiment.wraps
	def load_file(self,path: Path):
		"""Reads rheometer file to extract data of interest based on experiment type."""
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


	@magicclass(name="Visualization",layout="vertical",widget_type="groupbox")
	class PlotData:
		
		def __init__(self):
			self.cmap=plt.cm.viridis #default cmap	
		
		plot_storage_tooltip="Plots storage modulus for each test."
		plot_storage_modulus=field(PushButton,options={"enabled": True,"tooltip":plot_storage_tooltip})
		
		plot_loss_tooltip="Plots loss modulus for each test."
		plot_loss_modulus=field(PushButton,options={"enabled": True,"tooltip":plot_loss_tooltip})

		plot_relax_tooltip="Plots loss modulus for each test (stress relaxation)."
		plot_relax_modulus=field(PushButton,options={"enabled":True,"tooltip":plot_relax_tooltip,"visible":False})

		plot_averages_tooltip="Plots average storage and loss modulus. If tests \n are of different lengths, takes the longest common length for all tests."
		plot_averages=field(False,options={"label":"plot averages","tooltip":plot_averages_tooltip,"visible":False,
		"widget_type":CheckBox})

		colormap_tooltip = "Changes the colormap of the produced plots."
		colormap=field(str, options={"label": "Color map","choices":["Viridis",
		"Plasma", "Inferno","B&W"], "tooltip":colormap_tooltip})

		table_data_tooltip="Tabulated data for copying and pasting in further software of preference (e.g., Prism)"
		tabledata=field(Table, options={"label": "Experiment type", "tooltip":table_data_tooltip})


	@PlotData.wraps
	@PlotData.colormap.connect
	def _select_colormap(self): #those are all colorblind friendly cmaps
		if self.PlotData.colormap.value == "Viridis":
			self.PlotData.cmap = plt.cm.viridis
		if self.PlotData.colormap.value =="Plasma":
			self.PlotData.cmap= plt.cm.plasma
		if self.PlotData.colormap.value == "Inferno":
			self.PlotData.cmap=plt.cm.inferno
		if self.PlotData.colormap.value== "B&W":
			self.PlotData.cmap=plt.cm.Greys
	
	@PlotData.wraps
	def _update_colormap(self):
		if self.PlotData.colormap.changed: 
			#TODO:
			#update plot with current colormap
			plt.ion()

	@PlotData.wraps
	@PlotData.plot_averages.connect
	def _plot_averages(self):
		_, ax = plt.subplots(1, 1, figsize=(5,5))
		ax.set_yscale('log')
		ax.set_xscale('log')
		if self.PlotData.plot_averages.value is True:
			if self.PrepareExperiment.experiment.value=="strain sweep":
				x,y,y1=[],[],[]
				for i in range(len(self.data)):
					x.append(np.array(self.data[i])[:,0]) #strain
					y.append(np.array(self.data[i])[:,1]) #gprime
					y1.append(np.array(self.data[i])[:,2]) #gdoubleprime
				xav,yav,yerr=motor.getMedCurve(x,y,threshold=2,error=True)
				xav1,yav1,yerr1=motor.getMedCurve(x,y1,threshold=2,error=True)
				ax.errorbar(xav,yav,yerr=yerr,label="$G^{I}$")
				ax.errorbar(xav1,yav1,yerr=yerr1,label="$G^{II}$")
				ax.set_xlabel("Strain (%)")
				ax.set_ylabel("Average Moduli (Pa)")
				plt.legend()
				plt.show()

			if self.PrepareExperiment.experiment.value=="frequency sweep":
				x,y,y1=[],[],[]
				for i in range(len(self.data)):
					x.append(np.array(self.data[i])[:,0]) #frequency
					y.append(np.array(self.data[i])[:,1]) #gprime
					y1.append(np.array(self.data[i])[:,2]) #gdoubleprime
				xav,yav,yerr=motor.getMedCurve(x,y,threshold=2,error=True)
				xav1,yav1,yerr1=motor.getMedCurve(x,y1,threshold=2,error=True)
				ax.errorbar(xav,yav,yerr=yerr,label="$G^{I}$")
				ax.errorbar(xav1,yav1,yerr=yerr1,label="$G^{II}$")
				ax.set_xlabel("Frequency (rad/s)")
				ax.set_ylabel("Average Moduli (Pa)")
				plt.legend()
				plt.show()

			if self.PrepareExperiment.experiment.value=="stress relaxation":
				x,y=[],[]
				for i in range(len(self.data)):
					x.append(np.array(self.data[i])[:,0]) #time
					#y.append(np.array(self.data[i])[:,1]) #stress
					y.append(np.array(self.data[i])[:,2]) #relaxation modulus
				#xav,yav,yerr=motor.getMedCurve(x,y,threshold=2,error=True)
				xav,yav,yerr=motor.getMedCurve(x,y,threshold=2,error=True)
				#ax.errorbar(xav,yav,yerr=yerr,label="$G^{I}$")
				ax.errorbar(xav,yav,yerr=yerr,label="$G(t)$")
				ax.set_xlabel("Time (s)")
				ax.set_ylabel("$G(t)$ (Pa)")
				plt.legend()
				plt.show()
				
		if self.PlotData.plot_averages.value is False:
			plt.close(_)

	@PlotData.wraps
	@PlotData.plot_storage_modulus.connect
	def _plot_storage_modulus(self):
		fig, ax = plt.subplots(1, 1, figsize=(5,5))
		ax.set_yscale('log')
		ax.set_xscale('log')
		fig.suptitle('Storage Modulus')
		ax.set_ylabel('$G^{I}$ (Pa)')
		cols=[self.PlotData.cmap(i) for i in np.linspace(0,1,len(self.data))]
		for i in range(len(self.data)):
			ax.plot(np.array(self.data[i])[:,0], np.array(self.data[i])[:,1],label=self.names[i],color=cols[i])
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
		fig, ax1 = plt.subplots(1, 1, figsize=(5,5))
		ax1.set_yscale('log')
		ax1.set_xscale('log')
		fig.suptitle('Loss Modulus')
		ax1.set_ylabel('$G^{II}$ (Pa)')
		cols=[self.PlotData.cmap(i) for i in np.linspace(0,1,len(self.data))]
		for i in range(len(self.data)):
			ax1.plot(np.array(self.data[i])[:,0], np.array(self.data[i])[:,2],label=self.names[i],color=cols[i])
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
		fig, ax2 = plt.subplots(1, 1, figsize=(5,5))
		ax2.set_yscale('log')
		ax2.set_xscale('log')
		fig.suptitle('Relaxation Modulus')
		ax2.set_ylabel('$G(t)$ (Pa)')
		ax2.set_xlabel('t (s)')
		cols=[self.PlotData.cmap(i) for i in np.linspace(0,1,len(self.data))]
		for i in range(len(self.data)):
			ax2.plot(np.array(self.data[i])[:,0], np.array(self.data[i])[:,2],label=self.names[i],color=cols[i])
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
	
	@PlotData.wraps
	def _print_selected(self):
		#This cannot be done with magicgui
		pass

	def show_help(self):
		"""Shows help in navigating the gui."""
		build_help(self).show()

if __name__ == "__main__":
	ui = BulkRheoGUI()
	ui.show()
	#ui.macro.widget.show()
