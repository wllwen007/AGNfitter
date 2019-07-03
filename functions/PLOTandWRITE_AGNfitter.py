

"""%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

      PLOTandWRITE_AGNfitter.py

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

This script contains all functions used in order to visualize the output of the sampling.
Plotting and writing. 
These functions need the chains saved in files samples_mcmc.sav and samples_bur-in.sav.
This script includes:

- main function
- class OUTPUT
- class CHAIN
- class FLUXESARRAYS
- functions SED_plotting_settings, SED_colors

"""
#PYTHON IMPORTS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rc, ticker
import sys, os
import math 
import numpy as np
import corner #Author: Dan Foreman-Mackey (danfm@nyu.edu)
import time
import scipy
from astropy import units as u
from astropy import constants as const

#AGNfitter IMPORTS
import MODEL_AGNfitter as model
import PARAMETERSPACE_AGNfitter as parspace
import cPickle



def main(data, P, out):


    """
    Main function of PLOTandWRITE_AGNfitter. Output depends of settings in RUN_AGNfitter.

    ##input:
    - data object
    - dictionary P (parameter space settings)
    - dictionary out (output settings)
    
    """



    chain_burnin = CHAIN(data.output_folder+str(data.name)+ '/samples_burn1-2-3.sav', out)
    chain_mcmc = CHAIN(data.output_folder+str(data.name)+ '/samples_mcmc.sav',  out)
    chain_mcmc.props()

    print '_________________________________'
    print 'Properties of the sampling results:'
    print '- Mean acceptance fraction', chain_mcmc.mean_accept
    print '- Mean autocorrelation time', chain_mcmc.mean_autocorr

    output = OUTPUT(chain_mcmc, data)

    if out['plot_tracesburn-in']:
        fig, nplot=chain_burnin.plot_trace(P)
        fig.suptitle('Chain traces for %i of %i walkers.' % (nplot,chain_burnin.nwalkers))
        fig.savefig(data.output_folder+str(data.name)+'/traces_burnin.' + out['plot_format'])
        plt.close(fig)

    if out['plot_tracesmcmc']:
        fig, nplot = chain_mcmc.plot_trace(P)
        fig.suptitle('Chain traces for %i of %i walkers.'% (nplot,chain_mcmc.nwalkers))
        fig.savefig(data.output_folder+str(data.name)+'/traces_mcmc.' + out['plot_format'])
        plt.close(fig)

    if out['writepar_meanwitherrors']:
        outputvalues, outputvalues_header = output.write_parameters_outputvalues(P)
        comments_ouput= ' # Output for source ' +str(data.name) + '\n' +' Rows are: 2.5, 16, 50, 84, 97.5 percentiles, max likelihood # '+'\n'+ '-----------------------------------------------------'+'\n' 
        np.savetxt(data.output_folder + str(data.name)+'/parameter_outvalues_'+str(data.name)+'.txt' , outputvalues, delimiter = " ",fmt= "%1.4f" ,header= outputvalues_header, comments =comments_ouput)

    if out['plotSEDrealizations']:
        fig = output.plot_manyrealizations_SED()
        fig.savefig(data.output_folder+str(data.name)+'/SED_manyrealizations_' +str(data.name)+ '.'+out['plot_format'])
        plt.close(fig)
        
    if out['plot_posteriortriangle'] :
        #try:
        fig = output.plot_PDFtriangle('10pars', P.names)
        fig.savefig(data.output_folder+str(data.name)+'/PDFtriangle_10pars_'+str(data.name)+'.' + out['plot_format'])
        plt.close(fig)
        #except:
        #print 'Failed to plot pdf triangle'

    if out['plot_posteriortrianglewithluminosities']: 
        labels = [s.replace('_','\_') for s in out['intlum_names']]
        fig = output.plot_PDFtriangle('int_lums', labels) 
        fig.savefig(data.output_folder+str(data.name)+'/PDFtriangle_intlums_'+str(data.name)+'.' + out['plot_format'])
        plt.close(fig)





"""=========================================================="""


class OUTPUT:

    """
    Class OUTPUT

    Includes the functions that return all output products.
    You can call all chain and data properties, since it inherits chain and data classes.

    ##input: 
    - object of the CHAIN class, object of DATA class
    """    

    def __init__(self, chain_obj, data_obj):

        self.chain = chain_obj
        self.chain.props()

        self.out = chain_obj.out
        self.data = data_obj
        self.z=self.data.z
        fluxobj_withintlums = FLUXES_ARRAYS(chain_obj, self.out,'int_lums')
        fluxobj_4SEDplots = FLUXES_ARRAYS(chain_obj, self.out,'plot')

        if self.out['calc_intlum']:
            fluxobj_withintlums.fluxes( self.data)
            self.nuLnus = fluxobj_withintlums.nuLnus4plotting
            self.allnus = fluxobj_withintlums.all_nus_rest
            self.int_lums = fluxobj_withintlums.int_lums
            self.int_lums_best = fluxobj_withintlums.int_lums_best

        if self.out['plotSEDrealizations']:
            fluxobj_4SEDplots.fluxes(self.data)
            self.nuLnus = fluxobj_4SEDplots.nuLnus4plotting
            self.filtered_modelpoints_nuLnu = fluxobj_4SEDplots.filtered_modelpoints_nuLnu
            self.allnus = fluxobj_4SEDplots.all_nus_rest


    def write_parameters_outputvalues(self, P):        


        Mstar0, SFR_opt0 = model.stellar_info_array(np.array([self.chain.best_fit_pars]), self.data, 1)
        Mstar, SFR_opt = model.stellar_info_array(self.chain.flatchain_sorted, self.data, self.out['realizations2int'])
        column_names = np.transpose(np.array(["P025","P16","P50","P84","P975"], dtype='|S3'))
        chain_pars_best = np.hstack((self.chain.best_fit_pars, Mstar0, SFR_opt0))
        chain_pars = np.column_stack((self.chain.flatchain_sorted, Mstar, SFR_opt))        
                                            # np.mean(chain_pars, axis[0]),
                                            # np.std(chain_pars, axis[0]),
        if self.out['calc_intlum']:            

            

            SFR_IR = model.sfr_IR(self.int_lums[0]) #check that ['intlum_names'][0] is always L_IR(8-100)  
            SFR_IR_best = model.sfr_IR(np.array([self.int_lums_best[0]])) #check that ['intlum_names'][0] is always L_IR(8-100)         

            chain_others =np.column_stack((self.int_lums.T, SFR_IR))
            chain_others_best =np.hstack((self.int_lums_best.T, SFR_IR_best))
            
            outputvalues = np.column_stack((np.transpose(map(lambda v: (v[0],v[1],v[2],v[3],v[4]), zip(*np.percentile(chain_pars, [2.5,16, 50, 84,97.5], axis=0)))),
                                            np.transpose(map(lambda v: (v[0],v[1],v[2],v[3],v[4]), zip(*np.percentile(chain_others, [2.5,16, 50, 84,97.5], axis=0)))),
                                            np.transpose(np.percentile(self.chain.lnprob_flat, [2.5,16, 50, 84,97.5], axis=0)) ))  
            print chain_pars_best
            print chain_others_best
            print np.max(self.chain.lnprob_flat)
            
            outputvalues_best = np.hstack( (chain_pars_best, chain_others_best, np.max(self.chain.lnprob_flat)) )
            outputvalues = np.vstack((outputvalues, outputvalues_best))
            

            #y=x
    
            outputvalues_header= ' '.join([ i for i in np.hstack((P.names, 'log Mstar', 'SFR_opt', self.out['intlum_names'], 'SFR_IR', '-ln_like'))] )

        else:
            outputvalues = np.column_stack((map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]), zip(*np.percentile(chain_pars, [16, 50, 84],  axis=0))))) 
            outputvalues_header=' '.join( [ i for i in P.names] )
        return outputvalues, outputvalues_header

    def write_parameters_outputvalues1(self, P):        

        Mstar, SFR_opt = model.stellar_info_array(self.chain.flatchain_sorted, self.data, self.out['realizations2int'])
        column_names = np.transpose(np.array(["P025","P16","P50","P84","P975"], dtype='|S3'))
        chain_pars = np.column_stack((self.chain.flatchain_sorted, Mstar, SFR_opt))        
                                            # np.mean(chain_pars, axis[0]),
                                            # np.std(chain_pars, axis[0]),
        if self.out['calc_intlum']:            


            SFR_IR = model.sfr_IR(self.int_lums[0]) #check that ['intlum_names'][0] is always L_IR(8-100)        

            chain_others =np.column_stack((self.int_lums.T, SFR_IR))
            outputvalues = np.column_stack((np.transpose(map(lambda v: (v[0],v[1],v[2],v[3],v[4]), zip(*np.percentile(chain_pars, [2.5,16, 50, 84,97.5], axis=0)))),
                                            np.transpose(map(lambda v: (v[0],v[1],v[2],v[3],v[4]), zip(*np.percentile(chain_others, [2.5,16, 50, 84,97.5], axis=0)))),
                                            np.transpose(np.percentile(self.chain.lnprob_flat, [2.5,16, 50, 84,97.5], axis=0)) ))  

            #y=x
    
            outputvalues_header= ' '.join([ i for i in np.hstack((P.names, 'log Mstar', 'SFR_opt', self.out['intlum_names'], 'SFR_IR', '-ln_like'))] )

        else:
            outputvalues = np.column_stack((map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]), zip(*np.percentile(chain_pars, [16, 50, 84],  axis=0))))) 
            outputvalues_header=' '.join( [ i for i in P.names] )
        return outputvalues, outputvalues_header

    def plot_PDFtriangle(self,parameterset, labels):        

        if parameterset=='10pars':
            figure = corner.corner(self.chain.flatchain, labels= labels, plot_contours=True, plot_datapoints = False, show_titles=True, quantiles=[0.16, 0.50, 0.84])
        elif parameterset == 'int_lums':
            figure = corner.corner(self.int_lums.T, labels= labels,   plot_contours=True, plot_datapoints = False, show_titles=True, quantiles=[0.16, 0.50, 0.84])
        return figure


    def plot_manyrealizations_SED(self):    


        #reading from valid data from object data
        ydata = self.data.fluxes[self.data.fluxes>0.]
        yerror = self.data.fluxerrs[self.data.fluxes>0.]
        yndflags = self.data.ndflag[self.data.fluxes>0.]
        Nrealizations = self.out['realizations2plot']

        #Data frequencies (obs and rest), and model frequencies
        data_nus_obs = 10**self.data.nus[self.data.fluxes>0.]
        data_nus_rest = data_nus_obs * (1+self.z) 
        data_nus = np.log10(data_nus_rest)

        all_nus =self.allnus
        all_nus_rest = 10**all_nus 
        all_nus_obs =  10**all_nus / (1+self.z) #observed

        distance= model.z2Dlum(self.z)
        lumfactor = (4. * math.pi * distance**2.)
        data_nuLnu_rest = ydata* data_nus_obs *lumfactor
        data_errors_rest= yerror * data_nus_obs * lumfactor

        SBnuLnu, BBnuLnu, GAnuLnu, TOnuLnu, TOTALnuLnu, BBnuLnu_deredd = self.nuLnus

        #plotting settings
        fig, ax1, ax2, axr = SED_plotting_settings_ar(all_nus_rest, data_nuLnu_rest)
        SBcolor, BBcolor, GAcolor, TOcolor, TOTALcolor= SED_colors(combination = 'a')
        lw= 1.
        
        alp = 0.25
        if Nrealizations == 1:
            alp = 1.0
        for i in range(Nrealizations):
            
            # last one is the max likelihood fit
            if i == Nrealizations -1:
                alp = 1
                lw = 2

            #Settings for model lines
            p2=ax1.plot(all_nus, SBnuLnu[i], marker="None", linewidth=lw, label="1 /sigma", color= SBcolor, alpha = alp)
            p3=ax1.plot(all_nus, BBnuLnu[i], marker="None", linewidth=lw, label="1 /sigma",color= BBcolor, alpha = alp)
            p4=ax1.plot(all_nus, GAnuLnu[i],marker="None", linewidth=lw, label="1 /sigma",color=GAcolor, alpha = alp)
            p5=ax1.plot( all_nus, TOnuLnu[i], marker="None",  linewidth=lw, label="1 /sigma",color= TOcolor ,alpha = alp)
            p1= ax1.plot( all_nus, TOTALnuLnu[i], marker="None", linewidth=lw,  label="1 /sigma", color= TOTALcolor, alpha= alp)

            det = [yndflags==1]
            upp = [yndflags==0]
            
            p6 = ax1.plot(data_nus, self.filtered_modelpoints_nuLnu[i][self.data.fluxes>0.],   marker='o', linestyle="None",markersize=5, color="red", alpha =alp)
            p6r = axr.plot(data_nus[det], (data_nuLnu_rest[det]-self.filtered_modelpoints_nuLnu[i][self.data.fluxes>0.][det])/data_errors_rest[det],   marker='o', mec="None", linestyle="None",markersize=5, color="red", alpha =alp)
            


            upplimits = ax1.errorbar(data_nus[upp], 2.*data_nuLnu_rest[upp], yerr= data_errors_rest[upp]/2, uplims = True, linestyle='',  markersize=5, color="black")
            (_, caps, _) = ax1.errorbar(data_nus[det], data_nuLnu_rest[det], yerr= data_errors_rest[det], capsize=4, linestyle="None", linewidth=1.5,  marker='o',markersize=5, color="black", alpha = 1)


        ax1.text(0.04, 0.92, r'XID='+str(self.data.name)+r', z ='+ str(self.z), ha='left', transform=ax1.transAxes )
        ax1.text(0.96, 0.92, 'max log-likelihood = {ml:.1f}'.format(ml=np.max(self.chain.lnprob_flat)), ha='right', transform=ax1.transAxes )
        #ax1.annotate(r'XID='+str(self.data.name)+r', z ='+ str(self.z)+'max log-likelihood = {ml:.1f}'.format(ml=np.max(self.chain.lnprob_flat)), xy=(0, 1),  xycoords='axes points', xytext=(20, 310), textcoords='axes points' )#+ ', log $\mathbf{L}_{\mathbf{IR}}$= ' + str(Lir_agn) +', log $\mathbf{L}_{\mathbf{FIR}}$= ' + str(Lfir) + ',  log $\mathbf{L}_{\mathbf{UV}} $= '+ str(Lbol_agn)
        print ' => SEDs of '+ str(Nrealizations)+' different realization were plotted.'


        return fig




"""=========================================================="""


class CHAIN:

    """
    Class CHAIN

    ##input: 
    - name of file, where chain was saved
    - dictionary of ouput setting: out

    ##bugs: 

    """     

    def __init__(self, outputfilename, out):
            self.outputfilename = outputfilename
            self.out = out

    def props(self):
        if os.path.lexists(self.outputfilename):
            f = open(self.outputfilename, 'rb')
            samples = cPickle.load(f)
            f.close()

            self.chain = samples['chain']
            nwalkers, nsamples, npar = samples['chain'].shape

            Ns, Nt = self.out['Nsample'], self.out['Nthinning']        
            self.lnprob = samples['lnprob']
            self.lnprob_flat = samples['lnprob'][:,0:Ns*Nt:Nt].ravel()

            isort = (- self.lnprob_flat).argsort() #sort parameter vector for likelihood
            lnprob_sorted = np.reshape(self.lnprob_flat[isort],(-1,1))
            self.lnprob_max = lnprob_sorted[0]


            self.flatchain = samples['chain'][:,0:Ns*Nt:Nt,:].reshape(-1, npar)

            chain_length = int(len(self.flatchain))

            self.flatchain_sorted = self.flatchain[isort]
            self.best_fit_pars = self.flatchain[isort[0]]

            self.mean_accept =  samples['accept'].mean()
            self.mean_autocorr = samples['acor'].mean()

        else:

            'Error: The sampling has not been perfomed yet, or the chains were not saved properly.'



    def plot_trace(self, P, nwplot=50):

        """ Plot the sample trace for a subset of walkers for each parameter.
        """
        #-- Latex -------------------------------------------------
        #rc('text', usetex=True)
        rc('font', family='serif')
        rc('axes', linewidth=1.5)
        #-------------------------------------------------------------
        self.props()

        self.nwalkers, nsample, npar = self.chain.shape
        nrows = npar + 1
        ncols =1     
        width=13

        fig, axes = plt.subplots(nrows, ncols, sharex=True, figsize=(width, width*1.6))
        fig.subplots_adjust(hspace=0.1,left=0.05,right=0.95,top=0.95,bottom=0.05)

        nwplot = min(nsample, nwplot)
        for i in range(npar):
            ax = axes[i]
            for j in range(0, self.nwalkers, max(1, self.nwalkers // nwplot)):
                ax.plot(self.chain[j,:,i], lw=0.5,  color = 'black', alpha = 0.3)
            ax.set_ylabel(P.names[i], fontsize=12)  

        ax = axes[-1]
        for j in range(0, self.nwalkers, max(1, self.nwalkers // nwplot)):
            ax.plot(self.lnprob[j,:], lw=0.5, color = 'black', alpha = 0.3)
        ax.set_ylabel(r'Likelihood', fontsize=12)   
        ax.set_xlabel(r'Steps', fontsize=12)
        #ax.set_ylabel(r'\textit{Walkers}',fontsize=12)

        return fig, nwplot


"""=========================================================="""



class FLUXES_ARRAYS:

    """
    This class constructs the luminosities arrays for many realizations from the parameter values
    Output is returned by FLUXES_ARRAYS.fluxes().
    
    ## inputs:
    - object of class CHAIN
    - dictionary of output settings, out
    - str giving output_type: ['plot', 'intlum',  'bestfit']

    ## output:
    - frequencies and nuLnus + ['filteredpoints', 'integrated luminosities', - ]
    """


    def __init__(self, chain_obj, out, output_type):
        self.chain_obj = chain_obj
        self.output_type = output_type
        self.out = out

    def fluxes(self, data):    

        """
        This is the main function of the class.
        """
        self.chain_obj.props()

        SBFnu_list = []
        BBFnu_list = []
        GAFnu_list= []
        TOFnu_list = []
        TOTALFnu_list = []
        BBFnu_deredd_list = []
        if self.output_type == 'plot':
            filtered_modelpoints_list = []


        gal_do,  irlum_dict, nh_dict, BBebv_dict,_ = data.dictkey_arrays
        # Take the last 4 dictionaries, which are for plotting. (the first 4 were at bands)
        _,_,_,_,STARBURSTFdict , BBBFdict, GALAXYFdict, TORUSFdict,_= data.dict_modelfluxes

        nsample, npar = self.chain_obj.flatchain.shape
        source = data.name

        if self.output_type == 'plot':
            
            self.chain_obj.props()
            t = self.chain_obj.best_fit_pars
            tarr = [np.array([ti]) for ti in t]
            tau, agelog, nh, irlum, SB ,BB, GA,TO, BBebv, GAebv= tarr
            
            if self.out['realizations2plot'] > 1:
                tau, agelog, nh, irlum, SB ,BB, GA,TO, BBebv, GAebv= self.chain_obj.flatchain[np.random.choice(nsample+1, (self.out['realizations2plot'])),:].T
                # replace last one with most prob
                tau[-1], agelog[-1], nh[-1], irlum[-1], SB[-1] ,BB[-1], GA[-1],TO[-1], BBebv[-1], GAebv[-1]= t
                
        elif self.output_type == 'int_lums':
            
            self.chain_obj.props()
            t = self.chain_obj.best_fit_pars
            
            
            tau, agelog, nh, irlum, SB ,BB, GA,TO, BBebv, GAebv= self.chain_obj.flatchain[np.random.choice(nsample+1, (self.out['realizations2int'])),:].T
            # replace last one with most prob
            tau[-1], agelog[-1], nh[-1], irlum[-1], SB[-1] ,BB[-1], GA[-1],TO[-1], BBebv[-1], GAebv[-1]= t
            
            
        elif self.output_type == 'best_fit':
            tau, agelog, nh, irlum, SB ,BB, GA,TO, BBebv, GAebv= self.chain_obj.best_fit_pars

        age = 10**agelog

        self.all_nus_rest = np.arange(11.5, 16, 0.001) 

        for g in range(len(tau)):


            # Pick dictionary key-values, nearest to the MCMC- parameter values
            irlum_dct = model.pick_STARBURST_template(irlum[g], irlum_dict)
            nh_dct = model.pick_TORUS_template(nh[g], nh_dict)
            ebvbbb_dct = model.pick_BBB_template(BBebv[g], BBebv_dict)
            gal_do.nearest_par2dict(tau[g], age[g], GAebv[g])
            tau_dct, age_dct, ebvg_dct=gal_do.t, gal_do.a,gal_do.e

            #Produce model fluxes at all_nus_rest for plotting, through interpolation
            all_gal_nus, gal_Fnus = GALAXYFdict[tau_dct, age_dct,ebvg_dct]   
            GAinterp = scipy.interpolate.interp1d(all_gal_nus, gal_Fnus, bounds_error=False, fill_value=0.)
            all_gal_Fnus = GAinterp(self.all_nus_rest)

            all_sb_nus, sb_Fnus= STARBURSTFdict[irlum_dct] 
            SBinterp = scipy.interpolate.interp1d(all_sb_nus, sb_Fnus, bounds_error=False, fill_value=0.)
            all_sb_Fnus = SBinterp(self.all_nus_rest)

            all_bbb_nus, bbb_Fnus = BBBFdict[ebvbbb_dct] 
            BBinterp = scipy.interpolate.interp1d(all_bbb_nus, bbb_Fnus, bounds_error=False, fill_value=0.)
            all_bbb_Fnus = BBinterp(self.all_nus_rest)

            all_bbb_nus, bbb_Fnus_deredd = BBBFdict['0.0']
            BBderedinterp = scipy.interpolate.interp1d(all_bbb_nus, bbb_Fnus_deredd, bounds_error=False, fill_value=0.)
            all_bbb_Fnus_deredd = BBderedinterp(self.all_nus_rest)

            all_tor_nus, tor_Fnus= TORUSFdict[nh_dct]
            TOinterp = scipy.interpolate.interp1d(all_tor_nus, np.log10(tor_Fnus), bounds_error=False, fill_value=0.)
            all_tor_Fnus = 10**(TOinterp(self.all_nus_rest))        


            if self.output_type == 'plot':
                par2 = tau[g], agelog[g], nh[g], irlum[g], SB[g] ,BB[g], GA[g] ,TO[g], BBebv[g], GAebv[g]
                filtered_modelpoints, _, _ = parspace.ymodel(data.nus,data.z, data.dictkey_arrays, data.dict_modelfluxes, *par2)
                

            #Using the costumized normalization 
            SBFnu =   (all_sb_Fnus /1e20) *10**float(SB[g]) 
            BBFnu = (all_bbb_Fnus /1e60) * 10**float(BB[g]) 
            GAFnu =   (all_gal_Fnus/ 1e18) * 10**float(GA[g]) 
            TOFnu =   (all_tor_Fnus/  1e-40) * 10**float(TO[g])
            BBFnu_deredd = (all_bbb_Fnus_deredd /1e60) * 10**float(BB[g])

            TOTALFnu =  SBFnu + BBFnu + GAFnu + TOFnu
            
            #Append to the list for all realizations
            SBFnu_list.append(SBFnu)
            BBFnu_list.append(BBFnu)
            GAFnu_list.append(GAFnu)
            TOFnu_list.append(TOFnu)
            TOTALFnu_list.append(TOTALFnu)
            BBFnu_deredd_list.append(BBFnu_deredd)
            #Only if SED plotting: do the same with the  modelled flux values at each data point 
            if self.output_type == 'plot':
                filtered_modelpoints_list.append(filtered_modelpoints)


        #Convert lists into Numpy arrays
        SBFnu_array = np.array(SBFnu_list)
        BBFnu_array = np.array(BBFnu_list)
        GAFnu_array = np.array(GAFnu_list)
        TOFnu_array = np.array(TOFnu_list)
        TOTALFnu_array = np.array(TOTALFnu_list)
        BBFnu_array_deredd = np.array(BBFnu_deredd_list)    

        #Put them all together to transport
        FLUXES4plotting = (SBFnu_array, BBFnu_array, GAFnu_array, TOFnu_array, TOTALFnu_array,BBFnu_array_deredd)
        #Convert Fluxes to nuLnu
        self.nuLnus4plotting = self.FLUXES2nuLnu_4plotting(self.all_nus_rest, FLUXES4plotting, data.z)

        #Only if SED plotting:
        if self.output_type == 'plot':
            filtered_modelpoints = np.array(filtered_modelpoints_list)
            distance= model.z2Dlum(data.z)
            lumfactor = (4. * math.pi * distance**2.)
            self.filtered_modelpoints_nuLnu = (filtered_modelpoints *lumfactor* 10**(data.nus))
        #Only if calculating integrated luminosities:    
        elif self.output_type == 'int_lums':
            int_lums = np.log10(self.integrated_luminosities(self.out ,self.all_nus_rest, self.nuLnus4plotting))
            self.int_lums = int_lums[:,:-1]  # all except last one which is best fit
            

            self.int_lums_best = int_lums[:,-1]  # last one
        # elif self.output_type == 'best_fit':
        #     self.filtered_modelpoints_nuLnu = self.FLUXES2nuLnu_4plotting(all_nus_rest,  filtered_modelpoints, self.chain_obj.data.z)
        
        


    def FLUXES2nuLnu_4plotting(self, all_nus_rest, FLUXES4plotting, z):

        """
        Converts FLUXES4plotting into nuLnu_4plotting.

        ##input: 
        - all_nus_rest (give in 10^lognu, not log.)
        - FLUXES4plotting : fluxes for the four models corresponding
                            to each element of the total chain
        - source redshift z                    
        """

        all_nus_obs = 10**all_nus_rest /(1+z) 
        distance= model.z2Dlum(z)
        lumfactor = (4. * math.pi * distance**2.)
        SBnuLnu, BBnuLnu, GAnuLnu, TOnuLnu, TOTALnuLnu, BBnuLnu_deredd = [ f *lumfactor*all_nus_obs for f in FLUXES4plotting]

        return SBnuLnu, BBnuLnu, GAnuLnu, TOnuLnu, TOTALnuLnu, BBnuLnu_deredd


    def integrated_luminosities(self,out ,all_nus_rest, nuLnus4plotting):

        """
        Calculates the integrated luminosities for 
        all model templates chosen by the user in out['intlum_models'], 
        within the integration ranges given by out['intlum_freqranges'].

        ##input: 
        - settings dictionary out[]
        - all_nus_rest
        - nuLnus4plotting: nu*luminosities for the four models corresponding
                            to each element of the total chain
        """

        SBnuLnu, BBnuLnu, GAnuLnu, TOnuLnu, TOTALnuLnu, BBnuLnu_deredd =nuLnus4plotting
        intlum_freqranges = (out['intlum_freqranges']*out['intlum_freqranges_unit']).to(u.Hz, equivalencies=u.spectral())
        int_lums = []
        for m in range(len(out['intlum_models'])):

            if out['intlum_models'][m] == 'sb':    
                nuLnu= SBnuLnu
            elif out['intlum_models'][m] == 'bbb':    
                nuLnu= BBnuLnu
            elif out['intlum_models'][m] == 'bbbdered':    
                nuLnu=BBnuLnu_deredd
            elif out['intlum_models'][m] == 'gal':    
                 nuLnu=GAnuLnu
            elif out['intlum_models'][m] == 'tor':    
                 nuLnu=TOnuLnu
        
            index  = ((all_nus_rest >= np.log10(intlum_freqranges[m][1].value)) & (all_nus_rest<= np.log10(intlum_freqranges[m][0].value)))            
            all_nus_rest_int = 10**(all_nus_rest[index])
            Lnu = nuLnu[:,index] / all_nus_rest_int
            Lnu_int = scipy.integrate.trapz(Lnu, x=all_nus_rest_int)
            int_lums.append(Lnu_int)

        return np.array(int_lums)



"""
Some stand-alone functions on the SED plot format
"""


def SED_plotting_settings_ar(x, ydata):

    """
    This function produces the setting for the figures for SED plotting.
    **Input:
    - all nus, and data (to make the plot limits depending on the data)
    """
    fig = plt.figure()
    ax1 = fig.add_axes([0.1,0.3,0.8,0.6])
    ax2 = ax1.twiny()
    axr = fig.add_axes([0.1,0.1,0.8,0.2],sharex=ax1)
    #axr = fig.add_axes([0.1,0.1,0.8,0.2])

    #-- Latex -------------------------------------------------
    #rc('text', usetex=True)
    rc('font', family='serif')
    rc('axes', linewidth=1.5)
    #-------------------------------------------------------------

    #    ax1.set_title(r"\textbf{SED of Type 2}" + r"\textbf{ AGN }"+ "Source Nr. "+ source + "\n . \n . \n ." , fontsize=17, color='k')   
    ax1.xaxis.set_visible(False)
    axr.set_xlabel(r'rest-frame ${\log \  \nu}$ $[\mathrm{Hz}] $', fontsize=13)
    ax2.set_xlabel(r'${\lambda}$ $[\mathrm{\mu m}] $', fontsize=13)
    ax1.set_ylabel(r'$\nu L(\nu)$ $[\mathrm{erg\ s}^{-1}]$',fontsize=13)
    axr.set_ylabel(r'residual $[\sigma]$',fontsize=13)

    #ax1.tick_params(axis='both',reset=False,which='major',length=8,width=1.)
    #ax1.tick_params(axis='both',reset=False,which='minor',length=4,width=1.)

    axr.set_autoscalex_on(True) 
    ax1.set_autoscalex_on(True) 
    ax1.set_autoscaley_on(True) 
    ax1.set_xscale('linear')
    axr.set_xscale('linear')
    axr.minorticks_on()
    ax1.set_yscale('log')


    mediandata = np.median(ydata)
    mindata = np.min(ydata)
    maxdata = np.max(ydata)
    #ax1.set_ylim(mediandata /50.,mediandata * 50.)
    ax1.set_ylim(mindata /10.,maxdata * 10.)

    ax2.set_xscale('log')
    ax2.set_yscale('log')
    #ax2.set_ylim( mediandata /50., mediandata * 50.)
    ax2.set_ylim( mindata /10., maxdata * 10.)


    ax2.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    #ax2.tick_params(axis='both',reset=False,which='major',length=8,width=1.5)
    #ax2.tick_params(axis='both',reset=False,which='minor',length=4,width=1.5)

    x2 = (2.98e14/ x)[::-1] # Wavelenght axis
    xr = np.log10(x[::-1]) # frequency axis

    axr.plot(xr, np.zeros(len(xr)), 'gray', alpha=1)
    ax2.plot(x2, np.ones(len(x2)), alpha=0)
    ax2.invert_xaxis()
    ax2.set_xticks([100., 10.,1., 0.1]) 


    return fig, ax1, ax2, axr


def SED_plotting_settings(x, ydata):

    """
    This function produces the setting for the figures for SED plotting.
    **Input:
    - all nus, and data (to make the plot limits depending on the data)
    """
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    ax2 = ax1.twiny()

    #-- Latex -------------------------------------------------
    #rc('text', usetex=True)
    rc('font', family='serif')
    rc('axes', linewidth=1.5)
    #-------------------------------------------------------------

    #    ax1.set_title(r"\textbf{SED of Type 2}" + r"\textbf{ AGN }"+ "Source Nr. "+ source + "\n . \n . \n ." , fontsize=17, color='k')    
    ax1.set_xlabel(r'rest-frame ${\log \  \nu} [\mathrm{Hz}] $', fontsize=13)
    ax2.set_xlabel(r'${\lambda} [\mathrm{\mu m}] $', fontsize=13)
    ax1.set_ylabel(r'${\nu L(\nu) [\mathrm{erg \ } \mathrm{ s}^{-1}]}$',fontsize=13)

    ax1.tick_params(axis='both',reset=False,which='major',length=8,width=1.5)
    ax1.tick_params(axis='both',reset=False,which='minor',length=4,width=1.5)

    ax1.set_autoscalex_on(True) 
    ax1.set_autoscaley_on(True) 
    ax1.set_xscale('linear')
    ax1.set_yscale('log')


    mediandata = np.median(ydata)
    mindata = np.min(ydata)
    maxdata = np.max(ydata)
    #ax1.set_ylim(mediandata /50.,mediandata * 50.)
    ax1.set_ylim(mindata /10.,maxdata * 10.)

    ax2.set_xscale('log')
    ax2.set_yscale('log')
    #ax2.set_ylim( mediandata /50., mediandata * 50.)
    ax2.set_ylim( mindata /10., maxdata * 10.)


    ax2.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax2.tick_params(axis='both',reset=False,which='major',length=8,width=1.5)
    ax2.tick_params(axis='both',reset=False,which='minor',length=4,width=1.5)

    x2 = (2.98e14/ x)[::-1] # Wavelenght axis

    ax2.plot(x2, np.ones(len(x2)), alpha=0)
    ax2.invert_xaxis()
    ax2.set_xticks([100., 10.,1., 0.1]) 


    return fig, ax1, ax2

def SED_colors(combination = 'a'):

    if combination=='a':   
        steelblue = '#4682b4'
        darkcyan ='#009acd'
        deepbluesky = '#008b8b'
        seagreen = '#2E8B57'    
        lila = '#68228B'
        darkblue='#123281'

    return seagreen, darkblue, 'orange', lila, 'red'

