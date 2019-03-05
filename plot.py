import os,sys,argparse,re
import json
import itertools

import matplotlib.pyplot as plt
from pylab import rc

import parse_trace
import crop

import logging
from pycommons import generic_logging
if __name__ == '__main__':
	generic_logging.init(level=logging.DEBUG)
logger = logging.getLogger(__file__)

import numpy as np
from collections import Counter

rc('font',**{'family':'serif','serif':['Times'], 'size': 7})
rc('text', usetex=True)
rc('legend', fontsize=6, labelspacing=0.2)

colors = {0 : 'r', 1 : 'b', 2 : 'g', 3 : 'k'}

rc('font',**{'family':'serif','serif':['Times'], 'size': 7})
rc('text', usetex=True)
#rc('legend', fontsize=6, labelspacing=0.2)
rc('legend', fontsize=7.5, labelspacing=0.2)
rc('xtick', labelsize=7)
rc('ytick', labelsize=7)

rasterized=False

def new_fig(width=3.3, height=2.5, size=None):
	if size is 'half':
		return plt.figure(figsize=(width/2, height/2))
	elif size is 'third':
		return plt.figure(figsize=(width/3, height/3))
	elif size is 'fourth':
		return plt.figure(figsize=(width/4, height/4))
	else:
		return plt.figure(figsize=(width, height))

def save_plot(outdir, name, fig=None, **kwargs):
	if outdir:
		path = os.path.join(outdir, name)
	else:
		path = name
	logger.info("path: %s" % (path))
	if fig:
		fig.savefig(path, bbox_inches='tight', rasterized=rasterized, **kwargs)
		plt.close(fig)
	else:
		plt.savefig(path, bbox_inches='tight', rasterized=rasterized, **kwargs)
		plt.close()
	crop.main(['crop.py', path])


def plot_cdf(points, ax, labels, xlabel, ylabel='\\textbf{CDF}', binwidth=0.01,
		title=None, color='k', legend=True, markers=False):
	if not isinstance(points, list):
		points = [points]
	if not labels:
		labels = [None for x in range(len(points))]
	if not color:
		color= [None for x in range(len(points))]
	assert len(points) == len(labels)

	_markers = ['o', 's', 'v', 'h', 'p', '8', 'D', 'x', '+', '*', 'd', '^']
	if not markers:
		markers = [None for x in points]
	else:
		markers = _markers
	assert len(markers) >= len(points), 'Not enough markers'

	for idx, pts, label, color in itertools.izip(xrange(len(points)), points, labels, color):
		try:
#			pts = sorted(pts)
			pts = round_list(pts)

			counts_dict = Counter(pts)
			unique_pts = sorted(set(pts))
			counts = [counts_dict[x] for x in unique_pts]
			cumsum = np.cumsum(counts)
			cumsum = [x / float(sum(counts)) for x in cumsum]
			x_axis = unique_pts
			# From 0
			cumsum.insert(0, 0)
			x_axis.insert(0, x_axis[0])
			logger.debug('len(cumsum): %d, len(xaxis): %d' % (len(cumsum), len(x_axis)))
			if not color:
				ax.plot(x_axis, cumsum, label=label, marker=markers[idx], markersize=3, markeredgewidth=0, rasterized=rasterized)
			else:
				ax.plot(x_axis, cumsum, label=label, marker=markers[idx], markersize=3, markeredgewidth=0, rasterized=rasterized, color=color)
		except Exception, e:
			print e
			continue

#	xmin = min(x_axis)
#	xmax = max(x_axis)
#	ax.set_xlim((min(x_axis), max(x_axis)
	ax.set_yticks(np.arange(0, 1.1, 0.2))

	ax.set_xlabel(xlabel)
	#XXX: We don't show CDF on every plot ...
	ax.set_ylabel(ylabel)

	if title:
		ax.set_title(title)

	if legend:
		ax.legend(loc='best', numpoints=1, markerscale=1.5)

def boxplot(ax, values, positions, width, color, **kwargs):
	overall_p85 = None
	kwargs['align'] = kwargs.get('align', 'edge')
	lines = []
	for v, p in itertools.izip(values, positions):
		if len(v) == 0:
			continue
		p25 = np.percentile(v, 25)
		p50 = np.percentile(v, 50)
		p75 = np.percentile(v, 75)
		line = ax.bar(p, p75-p25, bottom=p25, width=width, color=color, edgecolor='none', **kwargs)
		lines.append(line)
		if kwargs['align'] == 'center':
			ax.plot([p-width/2., p+width/2.], [p50, p50], color='w', linewidth=0.3)
		elif kwargs['align'] == 'edge':
			ax.plot([p, p+width], [p50, p50], color='w', linewidth=0.3)
	return lines

def round_list(values):
	return [_round(v) for v in values]

def _round(v):
	round_dict = {0.0001 : 3, 0.001 : 2, 0.01 : 1, 0.1 : 1, 1 : 1, 10 : 0, 100 : -1, 1000 : -2}
	round_list = sorted(round_dict.keys(), reverse=True)
	for r in round_list:
		if abs(v) > r:
			ret = round(v, round_dict[r])
			if ret == 0:
				ret = round(v, round_dict[r] + 1)
			return ret
	return v

kelly_colors_hex = [
	'#FFB300', # Vivid Yellow
	'#803E75', # Strong Purple
	'#FF6800', # Vivid Orange
	'#A6BDD7', # Very Light Blue
	'#C10020', # Vivid Red
	'#CEA262', # Grayish Yellow
	'#817066', # Medium Gray
	'#007D34', # Vivid Green
	'#F6768E', # Strong Purplish Pink
	'#00538A', # Strong Blue
	'#FF7A5C', # Strong Yellowish Pink
	'#53377A', # Strong Violet
	'#FF8E00', # Vivid Orange Yellow
	'#B32851', # Strong Purplish Red
	'#F4C800', # Vivid Greenish Yellow
	'#7F180D', # Strong Reddish Brown
	'#93AA00', # Vivid Yellowish Green
	'#593315', # Deep Yellowish Brown
	'#F13A13', # Vivid Reddish Orange
	'#232C16', # Dark Olive Green
]

colors = kelly_colors_hex

devices = [
	'1a28ea49f4206010fee054f9bdb86f822dc4dd28',
	'1b0676e5fb2d7ab82a2b76887c53e94cf0410826',
	'2747d54967a32fc95945671b930d57c1d5a9ac02',
	'4affacf02c96acd83e34d8085159150b753105bb',
	'52a71d8a0140f8b994fa1b69492dd41a7cfc4b4f',
	'545e7aba064dd4e65e8c22caa909489657898afe',
	'8860ffed77873823ef1e971db16631ea4d26d635',
	'9714ee0ce5a5d75710902d79e0dd34e683d1ae76',
	'bca9d14152d010ab203dffd36d75b0da84ac4767',
	'ed05b5fafc2aa4aa7a0f2527f918fb1f3272ce8a',
]

markers = ['o', 's', 'v', 'h', 'p', '8', 'D', 'x', '+', '*', 'd', '^']

device_colors = {}
for d, c in itertools.izip(devices, colors):
	device_colors[d] = c
