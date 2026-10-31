"""Invented public fixtures only: no Measurement DB questions/outcomes or API records."""
import json,sqlite3
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from r1api.util import sha,content_hash
def make_database(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);(root/'traces').mkdir(exist_ok=True)
    (root/'active_permission_policy.json').write_text(json.dumps({'quarantined_inventory_matches':{}}))
    path=root/'synthetic.sqlite';c=sqlite3.connect(path)
    c.executescript('''
    create table benchmarks(family text primary key,card text,source text,license text);
    create table subjects(family text,sid text,name text,normalized text,provider text,harness text,config text,primary key(family,sid)) without rowid;
    create table items(id integer primary key,family text,iid text,source_group text,content_hash text,source_key text,content text,representation text,features text,reference text,complete int,numeric_ok int,unique(family,iid));
    create table pair_stats(family text,sid text,iid text,cond text,n integer,k real,example_response text,primary key(family,sid,iid,cond)) without rowid;
    create table trace_catalog(family text primary key,path text,columns_json text,n_rows integer);
    create table subject_statistics(family text,sid text,cond text,n,k,items,source_groups,group_sum,group_square);
    create table item_statistics(family text,iid text,n,k,subjects);
    create virtual table benchmark_fts using fts5(family UNINDEXED,name,description,domain,modality);
    create virtual table item_fts using fts5(content,features,representation,content='items',content_rowid='id');
    ''')
    for f in ['synthetic','excluded']:
        card={'benchmark_id':f,'name':f,'description':'Invented arithmetic and code tasks','domain':'test','modality':'text'}
        c.execute('insert into benchmarks values(?,?,?,?)',(f,json.dumps(card),'synthetic fixture','MIT'))
        c.execute('insert into benchmark_fts values(?,?,?,?,?)',(f,f,card['description'],'test','text'))
        subject={'subject_id':'s1','normalized_name':'Invented model','provider':'Invented','harness':'invented'}
        c.execute('insert into subjects values(?,?,?,?,?,?,?)',(f,'s1','Invented model','inventedmodel','Invented','invented',json.dumps(subject)))
        c.execute('insert into subject_statistics values(?,?,?,?,?,?,?,?,?)',(f,'s1','default',2,1,2,2,1,1))
    items=[]
    for i,(f,text,source) in enumerate([('synthetic','Invented arithmetic example one','group-a'),('synthetic','Invented Python code example two','group-b'),('synthetic','Invented protected-source variant','shared'),('excluded','Invented excluded arithmetic','shared')],1):
        iid='i'+str(i);c.execute('insert into items values(?,?,?,?,?,?,?,?,?,?,?,?)',(i,f,iid,source,content_hash(text),source,text,text,'','','1',1))
        c.execute('insert into pair_stats values(?,?,?,?,?,?,?)',(f,'s1',iid,'default',1,i%2,'r'+str(i)))
        c.execute('insert into item_statistics values(?,?,?,?,?)',(f,iid,1,i%2,1));items.append({'family':f,'iid':iid})
    c.execute("insert into item_fts(item_fts) values('rebuild')")
    c.execute('insert into trace_catalog values(?,?,?,?)',('synthetic','unused','[]',1))
    c.commit();c.close()
    text='Synthetic trace '+('x'*4500)
    pq.write_table(pa.Table.from_pylist([{'response_id':'r1','trace':text[:4000],'r1_full_trace_sha256':bytes.fromhex(sha(text)),'r1_full_trace_chars':len(text)}]),root/'traces/synthetic.parquet')
    vectors=np.zeros((len(items),384),dtype=np.float32);vectors[:,0]=[1,.9,.8,.7];vectors[:,1]=np.sqrt(1-vectors[:,0]**2)
    np.save(root/'vectors.npy',vectors);(root/'items.json').write_text(json.dumps(items));(root/'semantic_manifest.json').write_text(json.dumps({'vectors':'vectors.npy','items':'items.json','model':'invented encoder fixture','representation_policy':'synthetic','families':['synthetic','excluded']}))
    return path
