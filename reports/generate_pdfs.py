"""Generate submission PDFs from the two Markdown reports.

This intentionally uses only the Python standard library so report export does
not add a runtime dependency to the application.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
PAGE_W, PAGE_H = 595, 842
MARGIN = 54

def safe(text):
    replacements = {"₹":"INR ", "–":"-", "—":"-", "→":"->", "≥":">=", "≤":"<=", "·":"-", "’":"'", "“":"\"", "”":"\"", "…":"..."}
    for old, new in replacements.items(): text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")

def escape(text): return safe(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

class PDF:
    def __init__(self, title):
        self.title=title; self.pages=[]
    def page(self):
        page={"ops":[],"y":PAGE_H-MARGIN}; self.pages.append(page); return page
    def text(self,page,x,y,text,size=10,font="F1",color=(.12,.18,.25)):
        r,g,b=color; page["ops"].append(f"{r:.3f} {g:.3f} {b:.3f} rg BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({escape(text)}) Tj ET")
    def line(self,page,x1,y1,x2,y2,color=(.82,.87,.9),width=0.6):
        r,g,b=color; page["ops"].append(f"{r:.3f} {g:.3f} {b:.3f} RG {width} w {x1} {y1} m {x2} {y2} l S")
    def rect(self,page,x,y,w,h,fill):
        r,g,b=fill; page["ops"].append(f"{r:.3f} {g:.3f} {b:.3f} rg {x} {y} {w} {h} re f")
    def write(self,path):
        objects=[None, "<< /Type /Catalog /Pages 3 0 R >>", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", ""]
        page_ids=[]
        for page_num,page in enumerate(self.pages,1):
            ops=list(page["ops"]); self.text(page,MARGIN,PAGE_H-28,self.title,8,"F1",(.38,.48,.56)); self.line(page,MARGIN,38,PAGE_W-MARGIN,38); self.text(page,PAGE_W-MARGIN-35,23,f"{page_num} / {len(self.pages)}",8,"F1",(.38,.48,.56))
            stream="\n".join(ops).encode("latin-1","replace"); content_id=len(objects); objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode('latin-1')}\nendstream")
            page_id=len(objects); objects.append(f"<< /Type /Page /Parent 3 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources << /Font << /F1 2 0 R /F2 2 0 R >> >> /Contents {content_id} 0 R >>"); page_ids.append(page_id)
        kids=" ".join(f"{x} 0 R" for x in page_ids); objects[3]=f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
        out=bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"); offsets=[0]
        for i,obj in enumerate(objects[1:],1): offsets.append(len(out)); out.extend(f"{i} 0 obj\n{obj}\nendobj\n".encode("latin-1"))
        xref=len(out); out.extend(f"xref\n0 {len(objects)}\n0000000000 65535 f \n".encode())
        for off in offsets[1:]: out.extend(f"{off:010d} 00000 n \n".encode())
        out.extend(f"trailer\n<< /Size {len(objects)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()); path.write_bytes(out)

def wrap(text,width=91):
    words=safe(text).split(); lines=[]; current=""
    for word in words:
        if len(current)+len(word)+1>width: lines.append(current); current=word
        else: current=(current+" "+word).strip()
    if current: lines.append(current)
    return lines or [""]

def markdown_blocks(path):
    lines=path.read_text(encoding="utf-8").splitlines(); blocks=[]; i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip(): i+=1; continue
        if line.startswith("```"):
            code=[]; i+=1
            while i<len(lines) and not lines[i].startswith("```"): code.append(lines[i]); i+=1
            i+=1; blocks.append(("code",code)); continue
        if line.startswith("|"):
            table=[]
            while i<len(lines) and lines[i].startswith("|"):
                cells=[c.strip() for c in lines[i].strip("|").split("|")]
                if not all(set(c)<=set("-: ") for c in cells): table.append(cells)
                i+=1
            blocks.append(("table",table)); continue
        if line.startswith("#"):
            level=len(line)-len(line.lstrip("#")); blocks.append((f"h{level}",line[level:].strip())); i+=1; continue
        paragraph=[line]; i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(("#","|","```")): paragraph.append(lines[i]); i+=1
        blocks.append(("p", " ".join(paragraph)))
    return blocks

def contents(pdf, blocks, title):
    p=pdf.page(); pdf.rect(p,0,0,PAGE_W,PAGE_H,(.06,.16,.26)); pdf.rect(p,0,0,PAGE_W,9,(.12,.55,.50)); pdf.text(p,64,560,title,28,"F1",(1,1,1)); pdf.text(p,64,525,"Submission-ready technical documentation",13,"F1",(.77,.91,.90)); pdf.text(p,64,490,"Verified local proof of concept | Synthetic demonstration data",10,"F1",(.77,.91,.90));
    p=pdf.page(); pdf.text(p,MARGIN,PAGE_H-76,"Contents",22,"F1",(.06,.16,.26)); y=PAGE_H-116
    for kind,value in blocks:
        if kind in {"h1","h2"}:
            indent=0 if kind=="h1" else 16; pdf.text(p,MARGIN+indent,y,safe(value),11 if kind=="h1" else 10); y-=18 if kind=="h1" else 15
            if y<70: p=pdf.page(); y=PAGE_H-70

def render(pdf,blocks,title):
    contents(pdf,blocks,title)
    if "Technical" in title:
        p=pdf.page(); pdf.text(p,MARGIN,PAGE_H-76,"Architecture at a glance",20,"F1",(.06,.16,.26)); pdf.text(p,MARGIN,PAGE_H-101,"The Streamlit layer orchestrates services, persistence, and model inference.",10)
        boxes=[("Streamlit UI",MARGIN,560,130,58,(.09,.32,.38)),("Business services",230,560,135,58,(.12,.55,.50)),("SQLite / SQLAlchemy",405,560,135,58,(.09,.32,.38)),("ML pipeline",230,430,135,58,(.12,.55,.50)),("Plotly analytics",405,430,135,58,(.09,.32,.38))]
        for label,x,y,w,h,color in boxes: pdf.rect(p,x,y,w,h,color); pdf.text(p,x+12,y+25,label,10,"F1",(1,1,1))
        for x1,y1,x2,y2 in [(184,589,230,589),(365,589,405,589),(297,560,297,488),(365,459,405,459)]: pdf.line(p,x1,y1,x2,y2,(.12,.35,.38),2)
        pdf.text(p,MARGIN,335,"Collection state, verified payments, notification logs, and predictions remain auditable",10,"F1",(.24,.34,.42))
    p=pdf.page(); y=p["y"]
    for kind,value in blocks:
        if kind=="h1":
            if y<150: p=pdf.page(); y=p["y"]
            y-=8; pdf.text(p,MARGIN,y,safe(value),18,"F1",(.06,.16,.26)); y-=24; pdf.line(p,MARGIN,y,PAGE_W-MARGIN,y,(.12,.55,.50),1.5); y-=18
        elif kind=="h2":
            if y<100: p=pdf.page(); y=p["y"]
            y-=6; pdf.text(p,MARGIN,y,safe(value),13,"F1",(.06,.35,.34)); y-=20
        elif kind=="h3":
            y-=4; pdf.text(p,MARGIN,y,safe(value),11,"F1",(.12,.25,.35)); y-=16
        elif kind=="p":
            for line in wrap(value):
                if y<65: p=pdf.page(); y=p["y"]
                pdf.text(p,MARGIN,y,line,9.2); y-=13
            y-=5
        elif kind=="code":
            for line in value:
                if y<65: p=pdf.page(); y=p["y"]
                pdf.rect(p,MARGIN,y-3,PAGE_W-2*MARGIN,14,(.94,.97,.98)); pdf.text(p,MARGIN+6,y,safe(line),8,"F2",(.16,.28,.35)); y-=14
            y-=8
        elif kind=="table":
            if not value: continue
            widths=[(PAGE_W-2*MARGIN)/len(value[0])]*len(value[0]);
            for row_i,row in enumerate(value):
                row_h=20
                if y-row_h<55: p=pdf.page(); y=p["y"]
                if row_i==0: pdf.rect(p,MARGIN,y-row_h,PAGE_W-2*MARGIN,row_h,(.09,.32,.38))
                else: pdf.rect(p,MARGIN,y-row_h,PAGE_W-2*MARGIN,row_h,(.97,.98,.99) if row_i%2==0 else (1,1,1))
                x=MARGIN
                for cell,w in zip(row,widths): pdf.text(p,x+5,y-14," ".join(wrap(cell,22)[:1]),8,"F1",(1,1,1) if row_i==0 else (.12,.18,.25)); x+=w
                pdf.line(p,MARGIN,y-row_h,PAGE_W-MARGIN,y-row_h,(.82,.87,.9)); y-=row_h
            y-=10
    return pdf

def main():
    for source,name in [("AI_Opportunity_Report.md","TenantEase AI - AI Opportunity Report"),("Technical_Approach_Report.md","TenantEase AI - Technical Approach Report")]:
        blocks=markdown_blocks(REPORTS/source); pdf=PDF(name); render(pdf,blocks,name); pdf.write(REPORTS/(source.replace(".md",".pdf")))
        print(REPORTS/(source.replace(".md",".pdf")))

if __name__=="__main__": main()
