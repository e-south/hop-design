// Validate recorded projections before the browser commits a molecular view.
// Detailed comparisons and costs stay in records and exports, not duplicate UI.
export function validateInspectionFacts(identity, explanation, cost) {
  if(!identity)return;
  if(explanation?.materialized_realization_id!==identity || cost&&cost.materialized_realization_id!==identity)
    throw Error('Inspection facts disagree with the molecular identity.');
}
