// Same half-base curve contract as molecular/primitives/strand_curve.py.
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
const line = (a, b) => [a, mix(a, b, 1 / 3), mix(a, b, 2 / 3), b];
function halves([a, b, c, d]) {
  const ab = mix(a, b, .5), bc = mix(b, c, .5), cd = mix(c, d, .5);
  const abc = mix(ab, bc, .5), bcd = mix(bc, cd, .5), middle = mix(abc, bcd, .5);
  return [[a, ab, abc, middle], [middle, bcd, cd, d]];
}
export function bandSegments(points, start, end, terminalExtension = 6) {
  if (!(0 <= start && start <= end && end < points.length))
    throw new Error("A region requires an in-bounds ordered base interval.");
  if (points.length === 1) {
    const [x, y] = points[0];
    return [line([x - terminalExtension, y], [x + terminalExtension, y])];
  }
  const [first, second] = points, last = points.at(-1), penultimate = points.at(-2);
  const context = [mix(second, first, 2), ...points, mix(penultimate, last, 2)];
  const segments = [], distance = (a, b) => Math.max(Math.hypot(a[0] - b[0], a[1] - b[1]), 1e-9);
  if (start === 0) segments.push(line(mix(first, second, -terminalExtension / distance(first, second)), first));
  for (let i = Math.max(0, start - 1); i < Math.min(end + 1, points.length - 1); i++) {
    const [a, b, c, d] = context.slice(i, i + 4);
    let curve = [b, b.map((v, j) => v + (c[j] - a[j]) / 6), c.map((v, j) => v - (d[j] - b[j]) / 6), c];
    if (i < start) curve = halves(curve)[1];
    else if (i === end) curve = halves(curve)[0];
    segments.push(curve);
  }
  if (end === points.length - 1) segments.push(line(last, mix(last, penultimate, -terminalExtension / distance(last, penultimate))));
  return segments;
}
export function bandPath(points, start, end) {
  const segments = bandSegments(points, start, end);
  const xy = p => p.map(v => v.toFixed(4)).join(",");
  return "M" + xy(segments[0][0]) + segments.map(c => "C" + c.slice(1).map(xy).join(" ")).join(" ");
}

// Same fixed-width outline contract as molecular/primitives/ribbon.py.
export function ribbonPoints(points, halfWidth, start = 0, end = points.length - 1, terminalExtension = 8) {
  const left = [], right = [];
  bandSegments(points, start, end, terminalExtension).forEach(([a,b,c,d], ordinal) => {
    for (let step = ordinal === 0 ? 0 : 1; step <= 4; step++) {
      const t = step / 4, u = 1-t;
      const p = [0,1].map(k => u**3*a[k]+3*u*u*t*b[k]+3*u*t*t*c[k]+t**3*d[k]);
      const v = [0,1].map(k => 3*u*u*(b[k]-a[k])+6*u*t*(c[k]-b[k])+3*t*t*(d[k]-c[k]));
      const length = Math.max(Math.hypot(...v), 1e-9), nx = -v[1]*halfWidth/length, ny = v[0]*halfWidth/length;
      left.push([p[0]+nx,p[1]+ny]); right.push([p[0]-nx,p[1]-ny]);
    }
  });
  return [...left, ...right.reverse()];
}

export function roundedPath(points, radius = 2, sharp = new Set()) {
  const rows = [], xy = p => p.map(v=>v.toFixed(4)).join(",");
  points.forEach(([x,y], i) => {
    const previous=points[(i+points.length-1)%points.length], following=points[(i+1)%points.length];
    const before=Math.hypot(previous[0]-x,previous[1]-y), after=Math.hypot(following[0]-x,following[1]-y);
    const trim=sharp.has(i)?0:Math.min(radius,before/2,after/2);
    const a=[x+(previous[0]-x)*trim/Math.max(before,1e-9),y+(previous[1]-y)*trim/Math.max(before,1e-9)];
    const b=[x+(following[0]-x)*trim/Math.max(after,1e-9),y+(following[1]-y)*trim/Math.max(after,1e-9)];
    rows.push((i===0?"M":"L")+xy(a));
    if(trim) rows.push("Q"+xy([x,y])+" "+xy(b));
  });
  return rows.join(" ")+" Z";
}
export function ribbonPath(points, halfWidth, start=0, end=points.length-1, terminalExtension=8) {
  const outline=ribbonPoints(points,halfWidth,start,end,terminalExtension), n=outline.length/2, sharp=new Set();
  if(start) {sharp.add(0);sharp.add(outline.length-1);}
  if(end<points.length-1) {sharp.add(n-1);sharp.add(n);}
  return roundedPath(outline,2,sharp);
}
