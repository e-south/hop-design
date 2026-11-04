import {COLOR_KEYS,molecularColors} from './molecular_colors.js';

// Paint locally; export the same explicit lens through the shared saved view.
export function colorControls(host,onColor) {
  const select=host.querySelector('select[data-lens]'),words=host.querySelector('select[data-word]');
  const legend=host.querySelector('[data-color-legend]');
  let state=null,paths=null,axes=null,key=null,word=null,neutralMessage='';
  function initialKey(available,recipe=[]) {
    for(const candidate of new Set([...recipe,...available])) {
      if(!available.includes(candidate))continue;
      let first;
      for(const row of paths) {
        const value=row.values[candidate];if(value===undefined||value===null)continue;
        if(first!==undefined&&value!==first)return candidate;
        first=value;
      }
    }
    return 'none';
  }
  function show(prepared=null) {
    if(!state)return;
    const lens=prepared??molecularColors(paths,axes,{key,word});word=lens.word??null;
    words.hidden=lens.kind!=='word'||!lens.values.length;
    if(!words.hidden) {
      words.setAttribute('aria-label',`${lens.label} to highlight`);
      words.title='Counts show matching preparations; / total recorded when filters exclude preparations.';
      words.replaceChildren(...lens.values.map(v=>new Option(`${v.value} · ${v.eligible.toLocaleString()}${v.eligible===v.total?'':` / ${v.total.toLocaleString()}`}`,v.value)));
      words.value=word;
    }
    legend.replaceChildren();
    if(lens.kind==='numeric'&&lens.extent) {
      const caption=document.createElement('span');
      if(lens.constant) caption.textContent=`${lens.extent[0]} ${lens.unit} ${lens.missing?'where applicable':'throughout this edition'}`;
      else {
        const bar=document.createElement('i');bar.className='color-ramp';bar.setAttribute('aria-hidden','true');
        bar.style.background=`linear-gradient(to right,${lens.stops.join(',')})`;legend.append(bar);
        caption.textContent=`${lens.extent[0]}–${lens.extent[1]} ${lens.unit}`;
      }
      legend.append(caption);
    } else if(lens.kind!=='none'&&(lens.kind!=='word'||!word)) legend.textContent='Not applicable to these preparations';
    else if(neutralMessage)legend.textContent=neutralMessage;
    if(lens.missing&&lens.values.length){const missing=document.createElement('span');missing.textContent=`× ${lens.missing.toLocaleString()} without this coordinate`;legend.append(missing);}
    const outside=paths.filter(p=>!p.matches).length;
    if(outside){const text=document.createElement('span');text.textContent='Hollow: outside filters';legend.append(text);}
    host.dataset.colorKey=key;host.dataset.colorWord=word??'';onColor(lens);
  }
  const available=key=>Boolean(state&&state.presentation.landscape==='similarity'&&state.map_index&&
    (key==='none'||COLOR_KEYS.includes(key)&&axes.some(a=>a.key===key&&a.applicable!==false)));
  function choose(nextKey,value=null) {
    if(!available(nextKey))throw Error('This molecular color view is not available.');
    const lens=molecularColors(paths,axes,{key:nextKey,word:typeof value==='string'?value:null});
    key=nextKey;word=lens.word??null;neutralMessage='';select.value=key;show(lens);
  }
  const change=()=>choose(select.value,paths.find(p=>p.materialized_realization_id===state.selection?.materialized_realization_id)?.values[select.value]);
  const chooseWord=()=>{word=words.value;show();};
  select.addEventListener('change',change);words.addEventListener('change',chooseWord);
  return {
    available,choose,
    snapshot:()=>key===null?null:{key,word},
    update(next,{restore=false}={}) {
      // Validate before replacing the mounted lens, including when arrays are reused.
      const saved=restore||!state?next.presentation.color:null;
      const prepared=saved?molecularColors(next.choices.paths,next.choices.axes,saved):null;
      state=next;host.hidden=next.presentation.landscape!=='similarity'||!next.map_index;
      if(!restore&&!prepared&&next.choices.paths===paths&&next.choices.axes===axes)return;
      paths=next.choices.paths;axes=next.choices.axes;
      if(prepared){key=prepared.key;word=prepared.word??null;neutralMessage='';}
      else if(restore){key=null;word=null;}
      const available=COLOR_KEYS.filter(key=>axes.some(a=>a.key===key&&a.applicable!==false));
      if(!key||(key!=='none'&&!available.includes(key))){
        key=initialKey(available,next.presentation.display_axes??[]);
        const recorded=available.some(k=>paths.some(p=>p.values[k]!==null&&p.values[k]!==undefined));
        neutralMessage=key==='none'?(recorded?'Recorded color values are constant; inspect a point for values.':'No recorded color values.') : '';
      }
      if(word&&!paths.some(p=>p.values[key]===word))word=null;
      select.replaceChildren(...available.map(key=>new Option(axes.find(a=>a.key===key).label,key)),new Option('No grouping','none'));select.value=key;show(prepared);
    },
    close(){select.removeEventListener('change',change);words.removeEventListener('change',chooseWord);state=paths=axes=null;},
  };
}
