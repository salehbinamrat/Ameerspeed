// Test error classification without contacting the router or mutating session state.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('js/main.min.js','utf8');
const start = source.indexOf('function decodeHotspotError(');
const end = source.indexOf('function onLoginStart(',start);
assert(start>=0 && end>start);
const ctx={decodeURIComponent, String, RegExp, encodeURIComponent};
vm.runInNewContext(source.slice(start,end),ctx,{timeout:1000});
const cases=[
  ['not enough credit','NO_CREDIT'],
  ['transfer limit reached','DATA_LIMIT'],
  ['account expired','EXPIRED'],
  ['already logged in','SESSION_LIMIT'],
  ['user not found','USER_NOT_FOUND'],
  ['RADIUS timeout','AUTH_SERVER_UNAVAILABLE'],
  ['no valid profile found','NO_VALID_PROFILE'],
  ['some new router message','UNKNOWN']
];
for(const [input,want] of cases){
  const actual=ctx.classifyHotspotError(input,false);
  assert.equal(actual.code,want,`${input} -> ${actual.code}`);
  assert(actual.message.length>4);
}
console.log(`PASS ${cases.length} router error classification cases`);
