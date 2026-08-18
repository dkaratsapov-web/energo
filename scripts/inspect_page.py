# -*- coding: utf-8 -*-
"""Просмотр страницы: детекция строк + лента увеличенных кропов для вычитки."""
import cv2, numpy as np, sys, json
sys.path.insert(0,'scripts')
from textmask import find_lines

S='/tmp/claude-0/-home-user-energo/4f5fc398-702b-53db-bad5-51c1408b61d9/scratchpad/'

def inspect(page, boxes, dark=False, tag='', zoom=2.0, thr=18, k=31, gap=6, row_frac=0.012):
    img=cv2.imread(f'page_images_150dpi/pg{page:02d}.jpg')
    lines=[]
    for b in boxes:
        lines += find_lines(img,b,dark=dark,thr=thr,k=k,gap=gap,row_frac=row_frac)
    lines.sort(key=lambda l:(l[1],l[0]))
    vis=img.copy()
    for i,(x0,y0,x1,y1) in enumerate(lines):
        cv2.rectangle(vis,(x0,y0),(x1,y1),(0,0,255),2)
        cv2.putText(vis,str(i),(max(0,x0-26),y1),cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)
    cv2.imwrite(S+f'p{page:02d}{tag}_lines.jpg',cv2.resize(vis,(820,1160),interpolation=cv2.INTER_AREA),[1,92])
    # лента кропов
    strips=[]
    W=int(1100)
    for i,(x0,y0,x1,y1) in enumerate(lines):
        c=img[max(0,y0-6):y1+6, max(0,x0-6):x1+6]
        if c.size==0: continue
        s=cv2.resize(c,None,fx=zoom,fy=zoom,interpolation=cv2.INTER_CUBIC)
        if s.shape[1]>W: s=cv2.resize(s,(W,int(s.shape[0]*W/s.shape[1])),interpolation=cv2.INTER_AREA)
        pad=np.full((s.shape[0],W,3),30,np.uint8); pad[:,:s.shape[1]]=s
        lab=np.full((26,W,3),30,np.uint8)
        cv2.putText(lab,f'#{i}  x0={x0} y1={y1} w={x1-x0} h={y1-y0}',(4,19),cv2.FONT_HERSHEY_SIMPLEX,0.55,(0,255,255),1)
        strips += [lab,pad,np.full((4,W,3),90,np.uint8)]
    if strips: cv2.imwrite(S+f'p{page:02d}{tag}_strips.png',np.vstack(strips))
    print(json.dumps([{'i':i,'x0':l[0],'y0':l[1],'x1':l[2],'y1':l[3],'w':l[2]-l[0],'h':l[3]-l[1]}
                      for i,l in enumerate(lines)],ensure_ascii=False))
    return lines

if __name__=='__main__':
    page=int(sys.argv[1]); boxes=json.loads(sys.argv[2])
    kw=json.loads(sys.argv[3]) if len(sys.argv)>3 else {}
    inspect(page,[tuple(b) for b in boxes],**kw)
