// Prepare requested selected views off-screen; commit them within one paint opportunity.
export function coherentViews(prepareRoute, prepareTeaching, clear) {
  let serial = 0;
  return {
    async show(value, visible='both', beforeCommit=()=>{}) {
      if (!['both','molecule','route'].includes(visible)) throw Error('Unknown molecular view.');
      const ticket = ++serial;
      try {
        const [route, teaching] = await Promise.all([
          visible==='molecule'?null:prepareRoute(value),
          visible==='route'?null:prepareTeaching(value),
        ]);
        if (ticket !== serial) return;
        beforeCommit();
        route?.();
        teaching?.();
      } catch (error) {
        if (ticket !== serial) return;
        // Preparation happens off-screen. A failed new view must not erase the
        // previous committed selection; callers that already changed authority
        // explicitly clear it before exposing that different state.
        throw error;
      }
    },
    clear() { serial++; clear(); },
  };
}
