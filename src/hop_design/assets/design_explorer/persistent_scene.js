// A cohort drawing belongs to its artifact, not to the inspected preparation.
export function persistentScene(host) {
  let identity=null;
  return {
    matches(key) {return key===identity;},
    update(key, prepare) {
      if(key===identity) return false;
      const drawing=prepare();
      if(drawing) host.replaceChildren(drawing);
      identity=key;
      return true;
    },
    clear() {identity=null;host.replaceChildren();},
  };
}
