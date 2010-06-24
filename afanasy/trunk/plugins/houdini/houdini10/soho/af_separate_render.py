import hou
import os
import time

import af
import afhoudini

node = hou.pwd()
#asset = os.getenv('ASSET', os.getcwd())
#path = node.parm('files').eval()
f_start = int( node.parm('f1').eval())
f_finish = int( node.parm('f2').eval())
take = node.parm('take').eval()
#step_frame = int(pwd.parm('f3').eval())
job_name = node.parm('jobname').eval()
rop = node.parm('rop').eval()
run_rop = node.parm('run_rop').eval()
depend_mask = node.parm('depend_mask').eval()
tile_render = node.parm('tile_render').eval()
divx = node.parm('divx').eval()
divy = node.parm('divy').eval()

start_paused = node.parm('start_paused').eval()
platform = node.parm('platform').eval()
enable_extended_parameters = node.parm('enable_extended_parameters').eval()
priority = node.parm('priority').eval()
maximum_hosts = node.parm('maximum_hosts').eval()
capacity = node.parm('capacity').eval()
depend_mask_global = node.parm('depend_mask_global').eval()
hosts_mask = node.parm('hosts_mask').eval()
hosts_mask_exclude = node.parm('hosts_mask_exclude').eval()
capacity_min = node.parm('capacity_coefficient1').eval()
capacity_max = node.parm('capacity_coefficient2').eval()

images = afhoudini.pathToC( node.parm('images').evalAsStringAtFrame(f_start), node.parm('images').evalAsStringAtFrame(f_finish))

job = af.Job()
job.setName( job_name)
if platform != '':
   if platform == 'any': job.setNeedOS('')
   else: job.setNeedOS( platform)

if run_rop:
   ftime = time.time()
   tmphip = hou.hipFile.name() + '_' + job_name + time.strftime('.%m%d-%H%M%S-') + str(ftime - int(ftime))[2:5] + ".hip"
   # Use mwrite, because hou.hipFile.save(tmphip)
   # changes current scene file name to tmphip
   hou.hscript('mwrite -n %s' % tmphip)
   job.setCmdPost('rm ' + tmphip)
   b_generate = af.Block('generate', 'hbatch')
   b_generate.setCommand('hrender_af -s %1 -e %2 -b 1 -t '+take+' '+tmphip+' '+rop)
   b_generate.setNumeric( f_start, f_finish)

command = 'mantra'
tiles = divx * divy
b_render = af.Block('render', command)
if run_rop: b_render.setTasksDependMask('generate')
if tile_render:
   command = 'mantracroprender %(divx)d %(divy)d' % vars()
   b_render.setCommand( command + ' %1')
   b_render.setFramesPerTask( -tiles)
   for frame in range( f_start, f_finish + 1):
      arguments = node.parm('arguments').evalAsStringAtFrame( frame)
      for tile in range( 0, tiles):
         task = af.Task('%d tile %d' % ( frame, tile))
         task.setCommand( '%d %s' % ( tile, arguments))
         b_render.tasks.append( task)
else:
   arguments = afhoudini.pathToC( node.parm('arguments').evalAsStringAtFrame(f_start), node.parm('arguments').evalAsStringAtFrame(f_finish))
   b_render.setCommand( command + ' ' + arguments)
   b_render.setCommandView( images)
   b_render.setNumeric( f_start, f_finish)

if tile_render:
   cmd = 'exrjoin %(divx)d %(divy)d' % vars()
   b_join = af.Block('join', 'generic')
   b_join.setTasksDependMask('render')
   b_join.setCommand( '%s %s d' % ( cmd, images), False)
   b_join.setCommandView( images)
   b_join.setNumeric( f_start, f_finish)

if tile_render: job.blocks.append( b_join)
job.blocks.append( b_render)
if run_rop: job.blocks.append( b_generate)

job.setDependMask( depend_mask)

if enable_extended_parameters:
   job.setPriority( priority)
   if maximum_hosts > -1: job.setMaxHosts( maximum_hosts)
   if hosts_mask != '': job.setHostsMask( hosts_mask)
   if hosts_mask_exclude != '': job.setHostsMaskExclude( hosts_mask_exclude)
   if depend_mask_global != '': job.setDependMaskGlobal( depend_mask_global)
   b_generate.setCapacity( capacity)
   b_generate.setVariableCapacity( capacity_min, capacity_max)
   b_render.setCapacity( capacity)
   b_render.setVariableCapacity( capacity_min, capacity_max)
   b_join.setCapacity( capacity)
   b_join.setVariableCapacity( capacity_min, capacity_max)

if start_paused:
   job.offLine()

# Send job to Afanasy server.
job.send()
