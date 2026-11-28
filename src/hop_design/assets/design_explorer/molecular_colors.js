// Display only: measured values and names come from the admitted parameter rows.
export const COLOR_KEYS=['released_non_stem_nt','left_gap','right_gap','max_end_gap','loop_nt','foldback_arm_bp','loop_word','left_end_word','right_end_word'];
const accent='#0073E6',neutral='#8D99A5';
// Matched to presentation.palette.NUMERIC_DIVERGING by the print/browser parity test.
const ramp=[[49,54,149],[69,117,180],[116,173,209],[171,217,233],[224,243,248],[255,255,191],[254,224,144],[253,174,97],[244,109,67],[215,48,39],[165,0,38]];
function shade(t) {
  const last=ramp.length-1,index=Math.min(last-1,Math.floor(t*last)),fraction=t*last-index;
  return '#'+ramp[index].map((v,i)=>Math.round(v+(ramp[index+1][i]-v)*fraction).toString(16).padStart(2,'0')).join('');
}
export function colorAxes(axes,paths=[]) {
 if(paths.some(p=>p.overhead?.endpoint_non_payload_nt_by_strand&&Object.keys(p.overhead.endpoint_non_payload_nt_by_strand).length===2))axes=[...axes,{key:"released_non_stem_nt",label:"Released non-stem DNA",unit:"nt total",kind:"numeric",stage:"released_insert"}];
 const sides=['left_gap','right_gap'].map(key=>axes.find(a=>a.key===key&&a.applicable!==false));
 return sides.every(Boolean)?[...axes,{key:'max_end_gap',label:'Larger end gap',unit:'bp',kind:'numeric',stage:'released_insert'}]:axes;
}
export function colorValue(row,key) {
 if(key==='released_non_stem_nt'){
  const counts=row.overhead?.endpoint_non_payload_nt_by_strand;
  if(!counts||Object.keys(counts).length!==2)return null;
  const values=Object.values(counts);
  if(values.some(v=>!Number.isInteger(v)||v<0))throw Error('Released-insert color requires nonnegative strand nucleotide counts.');
  return values.reduce((a,b)=>a+b,0);
 }
 if(key!=='max_end_gap')return row.values[key];
 const ends=['left_gap','right_gap'].map(k=>row.values[k]);
 if(ends.some(v=>v===undefined||v===null))return null;
 if(ends.some(v=>typeof v!=='number'||!Number.isFinite(v)))throw Error('End-gap color requires finite numeric measurements.');
 return Math.max(...ends);
}
export function molecularColors(paths,axes,{key='none',word=null}={}) {
  if(key==='none') return {key,label:'No grouping',kind:'none',values:[],missing:0,color:()=>accent};
  const axis=colorAxes(axes,paths).find(a=>a.key===key);
  if(!COLOR_KEYS.includes(key)||!axis) throw Error('Unknown molecular color parameter.');
  const numeric=axis.kind==='numeric',counts=new Map();let missing=0;
  for(const row of paths) {
    const value=colorValue(row,key);
    if(value===undefined||value===null){missing++;continue;}
    if(numeric? !Number.isFinite(value)||typeof value!=='number' : typeof value!=='string')
      throw Error(`Invalid ${numeric?'numeric':'word'} color value.`);
    if(!counts.has(value))counts.set(value,{value,total:0,eligible:0});
    const count=counts.get(value);count.total++;count.eligible+=Number(row.matches);
  }
  const values=[...counts.values()].sort((a,b)=>numeric?a.value-b.value:a.value.localeCompare(b.value));
  const common={key,label:axis.label,unit:axis.unit,stage:axis.stage,values,missing};
  if(numeric) {
    const extent=values.length?[values[0].value,values.at(-1).value]:null;
    const constant=extent!==null&&extent[0]===extent[1];
    const colors=new Map(values.map(({value})=>[value,constant?accent:shade((value-extent[0])/(extent[1]-extent[0]))]));
    return {...common,kind:'numeric',extent,constant,stops:ramp.map((_,i)=>shade(i/(ramp.length-1))),color:row=>{
      return colors.get(colorValue(row,key))??null;
    }};
  }
  if(word!==null&&!counts.has(word)) throw Error('Choose an exact word in the recorded preparations.');
  word ??= values.slice().sort((a,b)=>b.total-a.total||a.value.localeCompare(b.value))[0]?.value??null;
  return {...common,kind:'word',word,color:row=>{
    const value=colorValue(row,key);return value===undefined||value===null?null:value===word?accent:neutral;
  }};
}
