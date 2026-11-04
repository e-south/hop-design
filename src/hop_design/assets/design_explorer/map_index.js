// Exact shared coordinates plus a bounded spatial lookup; no molecular inference.
export function pointIndex(data,rows) {
  if(data?.schema!=='hop.inspection-map/v1'||!Array.isArray(data.frame)||data.frame.length!==4||
     data.frame.some(v=>!Number.isFinite(v))||data.frame[2]<=0||data.frame[3]<=0||
     !Number.isFinite(data.radius)||data.radius<=0||!Array.isArray(data.points)||data.points.length!==rows.length)
    throw Error('Invalid molecular map index.');
  const seen=new Set(),cells=new Map(),positions=new Map(),cellSize=8;
  const points=data.points.map((p,order)=>{
    if(!Array.isArray(p)||p.length!==3||!Number.isInteger(p[0])||p[0]<0||p[0]>=rows.length||seen.has(p[0])||!p.slice(1).every(Number.isFinite))
      throw Error('Invalid molecular map member reference.');
    seen.add(p[0]);const point={order,row:rows[p[0]],x:p[1],y:p[2]};
    const position=`${point.x},${point.y}`;
    if(!positions.has(position))positions.set(position,{x:point.x,y:point.y,points:[]});
    point.group=positions.get(position);point.group.points.push(point);
    const key=`${Math.floor(point.x/cellSize)},${Math.floor(point.y/cellSize)}`;
    if(!cells.has(key))cells.set(key,[]);if(point.group.points.length===1)cells.get(key).push(point);return point;
  });
  return {points,groups:[...positions.values()],nearest(x,y,radius) {
    let found=null,best=radius**2;
    for(let a=Math.floor((x-radius)/cellSize);a<=Math.floor((x+radius)/cellSize);a++)
      for(let b=Math.floor((y-radius)/cellSize);b<=Math.floor((y+radius)/cellSize);b++)
        for(const p of cells.get(`${a},${b}`)||[]) {
          const distance=(x-p.x)**2+(y-p.y)**2;
          if(distance<best || distance===best&&(!found||p.order<found.order)){found=p;best=distance;}
        }
    return found;
  }};
}
