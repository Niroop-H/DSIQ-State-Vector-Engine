import assert from 'node:assert/strict';
import {rankSuite} from './rank-frame.test.mjs';
export function v09(test){
 test(19,'100-qubit connected encoded circuits, 500/1000/5000 interleaved T/TDG and Hadamards plus arbitrary rotations; all supported amplitude entries matched independent extended-precision oracle to 1e-13; fixed flip-rank family only, not arbitrary efficient T scaling',()=>{const a=rankSuite();assert.ok(a.scaling.every(s=>s.maxError<1e-13&&s.stats.coefficientBytes===a.scaling[0].stats.coefficientBytes));return a});
}
