// Display only: measured values and names come from the admitted parameter rows.
export const COLOR_KEYS=['left_gap','right_gap','loop_nt','foldback_arm_bp','loop_word','left_end_word','right_end_word'];
const accent='#216e72',neutral='#6a8186';
const ramp=[[223,235,230],[83,153,151],[26,62,75]];
function shade(t) {
  const index=Math.min(1,Math.floor(t*2)),fraction=t*2-index;
  return '#'+ramp[index].map((v,i)=>Math.round(v+(ramp[index+1][i]-v)*fraction).toString(16).padStart(2,'0')).join('');
}
export function molecularColors(paths,axes,{key='none',word=null}={}) {
  if(key==='none') return {key,label:'No grouping',kind:'none',values:[],missing:0,color:()=>accent};
  const axis=axes.find(a=>a.key===key);
  if(!COLOR_KEYS.includes(key)||!axis) throw Error('Unknown molecular color parameter.');
  const numeric=axis.kind==='numeric',counts=new Map();let missing=0;
  for(const row of paths) {
    const value=row.values[key];
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
    return {...common,kind:'numeric',extent,constant,stops:[shade(0),shade(.5),shade(1)],color:row=>{
      return colors.get(row.values[key])??null;
    }};
  }
  if(word!==null&&!counts.has(word)) throw Error('Choose an exact word in the recorded preparations.');
  word ??= values.slice().sort((a,b)=>b.total-a.total||a.value.localeCompare(b.value))[0]?.value??null;
  return {...common,kind:'word',word,color:row=>{
    const value=row.values[key];return value===undefined||value===null?null:value===word?accent:neutral;
  }};
}
