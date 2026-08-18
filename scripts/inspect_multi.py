# -*- coding: utf-8 -*-
"""Лента строк сразу по нескольким страницам — для вычитки текста пачкой."""
import cv2, numpy as np, sys, json
sys.path.insert(0,'scripts')
from textmask import find_lines
S='/tmp/claude-0/-home-user-energo/4f5fc398-702b-53db-bad5-51c1408b61d9/scratchpad/'

def run(jobs, out, zoom=2.0, W=1000):
    strips=[]; meta={}
    for job in jobs:
        pg=job['page']; img=cv2.imread(f'page_images_150dpi/pg{pg:02d}.jpg')
        lines=[]
        for b in job['boxes']:
            lines += find_lines(img, tuple(b), **job.get('kw',{}))
        lines.sort(key=lambda l:(l[1],l[0]))
        meta[pg]=[{'x0':l[0],'y0':l[1],'x1':l[2],'y1':l[3],'w':l[2]-l[0]} for l in lines]
        hdr=np.full((30,W,3),(60,20,20),np.uint8)
        cv2.putText(hdr,f'=== СТРАНИЦА {pg} ===',(6,22),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)
        strips.append(hdr)
        for i,(x0,y0,x1,y1) in enumerate(lines):
            c=img[max(0,y0-5):y1+5, max(0,x0-5):x1+5]
            if c.size==0: continue
            s=cv2.resize(c,None,fx=zoom,fy=zoom,interpolation=cv2.INTER_CUBIC)
            if s.shape[1]>W: s=cv2.resize(s,(W,int(s.shape[0]*W/s.shape[1])),interpolation=cv2.INTER_AREA)
            pad=np.full((s.shape[0],W,3),30,np.uint8); pad[:,:s.shape[1]]=s
            lab=np.full((20,W,3),30,np.uint8)
            cv2.putText(lab,f'{pg}#{i} x0={x0} y1={y1} w={x1-x0}',(4,15),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,255,255),1)
            strips += [lab,pad,np.full((3,W,3),90,np.uint8)]
    cv2.imwrite(S+out, np.vstack(strips))
    print(json.dumps(meta,ensure_ascii=False))

if __name__=='__main__':
    run(json.loads(sys.argv[1]), sys.argv[2])
