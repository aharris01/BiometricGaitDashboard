import numpy as np
from sort import *
from skimage.measure import label, regionprops
from skimage.morphology import remove_small_objects
import cv2
import pandas as pd
from itertools import combinations


import sys
import pathlib

import warnings
warnings.filterwarnings('ignore')

filename = pathlib.Path(sys.argv[1])
out_file = filename.with_suffix('.steps.npz')

print(f'{filename} => {out_file}')

if out_file.exists():
   print(f'\tskipping, {out_file} already exists...')
   sys.exit(0)


try:
  data = np.load(filename)['arr_0']


  """**Segment & Track Bounding Boxes**"""
  # minimum pixel threshold (helps remove noise)
  thresh = 10

  # combine bounding boxes with centroids within dist_px pixels
  dist_px = 30

  # dilation + erosion opts for preprocessing - may need to be adjusted
  dilation_shape = cv2.MORPH_ELLIPSE
  sz_d = 2 #4
  element_d = cv2.getStructuringElement(dilation_shape, (2 * sz_d + 1, 2 * sz_d + 1),(sz_d, sz_d))
  sz_e = 2
  element_e = cv2.getStructuringElement(dilation_shape, (2 * sz_e + 1, 2 * sz_e + 1),(sz_e, sz_e))

  # create motion tracker
  mot_tracker = Sort()

  # save bounding box coordinates & object labels for each frame
  d_all = []

  # max pixel value for rescaling
  img_max = data.max()

  # cycle through frames
  for i,frame_idx in enumerate(range(data.shape[0])):
      img_orig = (data[frame_idx]/img_max*255).astype(np.uint8)

      # get binary image
      img_bin = (img_orig>(thresh/img_max*255)).astype(np.uint8)

      # apply dilation & erosion
      img = cv2.dilate(img_bin,element_d, iterations=1)
      img = cv2.erode(img,element_e, iterations=1)

      # find bounding boxes for active regions
      img_label = label(img,connectivity=2)
      img_label = remove_small_objects(img_label,4)
      regions = regionprops(img_label)

      # merge nearby boxes
      centroids = np.array([props.centroid for props in regions])
      bboxes = np.array([props.bbox for props in regions])
      if len(regions) > 1:
          combs = combinations(np.arange(len(regions)),2)
          for idx,(b1,b2) in enumerate(combs):
            # calculate distance
            dist0 = abs(centroids[b2,0] - centroids[b1,0]) #np.linalg.norm(centroids[b1]-centroids[b2])
            dist1 = abs(centroids[b2,1] - centroids[b1,1])
            box1 = bboxes[b1]
            box2 = bboxes[b2]

            ## TODO TWEAK THIS TO MAKE IT WORK BETTER
            if (dist0 < dist_px) & (dist1 < dist_px/3):
              # merge boxes
              minr, minc, maxr, maxc = min(box1[0], box2[0]), min(box1[1], box2[1]), max(box1[2], box2[2]), max(box1[3], box2[3])
              bboxes[b1] = [minr,minc,maxr,maxc]
              bboxes[b2] = [minr,minc,maxr,maxc]

          # remove repeated bboxes
          bboxes = np.unique(bboxes, axis=0)

      # get detected object coordinates
      dets = np.zeros((len(bboxes),4))
      for j,bbox in enumerate(bboxes):
          minr, minc, maxr, maxc = bbox
          dets[j,:] = minc, minr, maxc, maxr

      # update motion trackers
      trackers = mot_tracker.update(dets)

      for d in trackers:
          # save bounding box coordinates & labels
          d_all.append(np.append(i,d).astype(int))

  d_all = np.array(d_all) # bounding box coordinates & labels

  if not len(d_all):
    print('\taborting, no footsteps found...')
    sys.exit(1)


  """**Extract 3D Footsteps**"""
  # function for getting bounding box overlap for merging
  def get_overlap(boxA, boxB):
      # determine the (x, y)-coordinates of the intersection rectangle
      xA = max(boxA[0], boxB[0])
      yA = max(boxA[1], boxB[1])
      xB = min(boxA[2], boxB[2])
      yB = min(boxA[3], boxB[3])

      # compute the area of intersection rectangle
      interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
      # compute the area of both boxes
      boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
      boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)

      overlap = max(interArea/boxAArea,interArea/boxBArea)

      return overlap

  time_padding = 5 # pad object by 5 frames before and after
  space_padding = 2 # pad object by 2 pixels on every side
  overlap_thresh = 0.4 # threshold for combining overlapping objects

  # find all objects detected by SORT
  unique_steps = np.unique(d_all[:,5])

  footstep_start = []
  footstep_end = []
  bbox_coords = []

  x_shape = data.shape[1]
  y_shape = data.shape[2]

  for step_ID in unique_steps:

    # get all frames
    idx = d_all[:,5] == step_ID

    # find start and end frames
    frame_start = d_all[idx,0].min()
    frame_end = d_all[idx,0].max()

    # get coordinates
    minr = max(d_all[idx,1].min(),0)
    minc = max(d_all[idx,2].min(),0)
    maxr = min(d_all[idx,3].max(),y_shape)
    maxc = min(d_all[idx,4].max(),x_shape)

    # pad a few frames before and after
    frame_start = max(frame_start - time_padding,0)
    frame_end = min(frame_end + time_padding,data.shape[0])

    # pad a few pixels on each side
    minr = max(minr - space_padding,0)
    minc = max(minc - space_padding,0)
    maxr = min(maxr + space_padding,y_shape)
    maxc = min(maxc + space_padding,x_shape)

    footstep_start.append(frame_start)
    footstep_end.append(frame_end)
    bbox_coords.append((minr,minc,maxr,maxc))

  bbox_coords = np.array(bbox_coords)
  footstep_start = np.array(footstep_start)
  footstep_end = np.array(footstep_end)

  # merge overlapping objects
  for i,j in combinations(np.arange(len(footstep_start)),2):

      # if overlapping in time, calculate spatial overlap
      if min(footstep_end[i],footstep_end[j])-max(footstep_start[i],footstep_start[j]) > 0:
          box1 = bbox_coords[i]
          box2 = bbox_coords[j]
          overlap = get_overlap(box1,box2)

          if overlap > overlap_thresh:
              # merge boxes
              minr, minc, maxr, maxc = min(box1[0], box2[0]), min(box1[1], box2[1]), max(box1[2], box2[2]), max(box1[3], box2[3])
              bbox_coords[i] = [minr,minc,maxr,maxc]
              bbox_coords[j] = [minr,minc,maxr,maxc]

              minf,maxf = min(footstep_start[i],footstep_start[j]), max(footstep_end[i],footstep_end[j])
              footstep_start[i] = minf
              footstep_end[i] = maxf
              footstep_start[j] = minf
              footstep_end[j] = maxf

  # delete repeats
  _,idx = np.unique(np.column_stack((bbox_coords,footstep_start,footstep_end)), return_index=True, axis = 0)
  idx = np.sort(idx)

  bbox_coords = bbox_coords[idx,:]
  footstep_start = footstep_start[idx]
  footstep_end = footstep_end[idx]

  # extract footsteps from raw data
  thresh_GRF = 0 # crop in time to where GRF > thresh_GRF
  thresh_pixel = 0 # crop spatially to where pixel values > thresh_pixel

  footsteps = []

  rm_idx = np.zeros(footstep_start.shape[0],dtype = bool)

  for i in range(len(footstep_start)):

      minr,minc,maxr,maxc = bbox_coords[i]
      frame_start = footstep_start[i]
      frame_end = footstep_end[i]

      footstep = data[frame_start:(frame_end+1),minc:(maxc+1),minr:(maxr+1)]

      # crop out any all zero frames
      nonzero_frames = np.where(footstep.sum((1,2))>thresh_GRF)[0]

      # get longest consecutive subsequence of non-zero frames
      consec_idx = np.where(np.diff(nonzero_frames)==1)[0]
      subseq = np.split(nonzero_frames[consec_idx],np.where(np.diff(consec_idx)!=1)[0]+1)
      longest_idx = np.argmax(np.array([s.shape[0] for s in subseq]))
      nonzero_frames = np.append(subseq[longest_idx],subseq[longest_idx][-1]+1)

      if nonzero_frames.any():

          frame_end = frame_start + nonzero_frames[-1]
          frame_start = frame_start + nonzero_frames[0]

          footstep_start[i] = frame_start
          footstep_end[i] = frame_end

          # crop to spatial region of interest
          nonzero_regions = np.where(footstep.sum((0))>thresh_pixel)

          maxr = minr + np.min([nonzero_regions[1].max()+1,footstep.shape[2]])
          minr = minr + np.max([nonzero_regions[1].min()-1,0])
          maxc = minc + np.min([nonzero_regions[0].max()+1,footstep.shape[1]])
          minc = minc + np.max([nonzero_regions[0].min()-1,0])
          bbox_coords[i,:] = [minr,minc,maxr,maxc]

          # update footstep
          footstep = data[frame_start:(frame_end+1),minc:(maxc+1),minr:(maxr+1)]

          footsteps.append(footstep)
      else:
          rm_idx[i] = True


  footstep_start = footstep_start[~rm_idx]
  footstep_end = footstep_end[~rm_idx]
  bbox_coords = bbox_coords[~rm_idx]

  # resort according to frame #
  sort_idx = np.argsort(footstep_start)
  footstep_start = footstep_start[sort_idx]
  footstep_end = footstep_end[sort_idx]
  bbox_coords = bbox_coords[sort_idx]
  footsteps = [footsteps[i] for i in sort_idx]

  # filter out objects that are too small
  # greater than 15 frames, 10 x 10 pixels
  idx = ((footstep_end - footstep_start) > 15) & ((bbox_coords[:,3]-bbox_coords[:,1]) > 10) & ((bbox_coords[:,2]-bbox_coords[:,0]) > 10)

  bbox_coords = bbox_coords[idx,:]
  footstep_start = footstep_start[idx]
  footstep_end = footstep_end[idx]
  footsteps = [footsteps[i] for i in np.where(idx)[0]]

  from scipy.ndimage import uniform_filter

  def remove_ghosting(footstep,thresh_factor = 100, delta_factor = 100):
      # remove zeros or non-changing segment from end of footstep
      GRF = footstep.sum((1,2)).astype(float)

      thresh = max(GRF)/thresh_factor # only remove segments with GRF < thresh
      delta = max(GRF)/delta_factor # minimum change in GRF

      is_changing = np.append(np.abs(np.diff(uniform_filter(GRF,5),1)) > delta,False)

      idx = (GRF < thresh) & (~is_changing) | (GRF == 0)

      last_val = GRF.shape[0] - np.where(np.flip(~idx))[0][0]
      footstep_cropped = footstep[0:last_val,:,:]

      # remove zeros or non-changing segment at beginning of footstep
      first_val = np.where(~idx)[0][0]
      footstep_cropped = footstep_cropped[first_val:,:,:]

      return footstep_cropped,first_val,last_val

  for i,footstep in enumerate(footsteps):
    footsteps[i],idx_start,idx_end = remove_ghosting(footstep)
    footstep_start[i] = footstep_start[i]+idx_start
    footstep_end[i] = footstep_end[i]-(footstep.shape[0]-idx_end)

  # resort according to frame #
  sort_idx = np.argsort(footstep_start)
  footstep_start = footstep_start[sort_idx]
  footstep_end = footstep_end[sort_idx]
  bbox_coords = bbox_coords[sort_idx]
  footsteps = [footsteps[i] for i in sort_idx]



  """**Save Footsteps and Metadata**"""

  footstep_file = filename.with_suffix('.steps.npz')
  metadata_file = filename.with_suffix('.metadata.csv')

  footstep_dict = {str(i):f for i, f in enumerate(footsteps)}
  np.savez_compressed(footstep_file, **footstep_dict)



  metadata_df = pd.DataFrame({
    'FootstepID': range(len(footsteps)),
    'StartFrame': footstep_start,
    'EndFrame': footstep_end,
    'YMin': bbox_coords[:, 1],
    'YMax': bbox_coords[:, 3],
    'XMin': bbox_coords[:, 0],
    'XMax': bbox_coords[:, 2],
  })

  metadata_df.to_csv(metadata_file, index=False)

except Exception as e:
   print(f'\tException occured while processing {out_file}: {e}')