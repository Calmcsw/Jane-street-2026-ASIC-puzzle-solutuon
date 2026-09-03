#!/usr/bin/env node
// convert_to_digitaljs.js - Convert an already-generated Yosys JSON netlist
// (produced by our own netlist_to_json.py pipeline) into a DigitalJS JSON
// circuit definition, using yosys2digitaljs purely as a library (no
// internal Yosys re-invocation, since we already did that step ourselves
// with our own cleanup: decap/fill/tap cell removal, specify-block
// stripping, pullup/pulldown replacement, power-pin stripping, etc).
//
// Usage:
//   node convert_to_digitaljs.js INPUT_YOSYS.json OUTPUT_DIGITALJS.json

const fs = require('fs');
const path = require('path');
const core = require('./yosys2digitaljs/dist/core.js');

const [, , inputPath, outputPath, topModule] = process.argv;
if (!inputPath || !outputPath) {
    console.error('Usage: node convert_to_digitaljs.js INPUT_YOSYS.json OUTPUT_DIGITALJS.json [TOP_MODULE_NAME]');
    process.exit(1);
}

const yosysJson = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const options = {
    // don't propagate constants / optimize away structure - we want to see
    // the real gate-level netlist, not a re-optimized version of it
    optimize: false,
};

let result;
try {
    if (topModule) {
        // Bypass yosys2digitaljs()'s topological-sort "guess the top module"
        // heuristic: it picks the wrong module when hundreds of blackbox
        // library cells (our sky130 standard cells, read via `-lib`) have
        // no dependencies of their own, making the sort ambiguous. Build
        // the same {devices, connectors, subcircuits} shape ourselves,
        // using our own known top-level module name.
        if (!(topModule in yosysJson.modules)) {
            throw new Error('top module "' + topModule + '" not found in JSON; available: ' +
                Object.keys(yosysJson.modules).slice(0, 20).join(', ') + ' ...');
        }
        const portmaps = core.order_ports(yosysJson);
        const out = core.yosys_to_digitaljs(yosysJson, portmaps, options);
        result = Object.assign({ subcircuits: {} }, out[topModule]);
        for (const name of Object.keys(out)) {
            if (name !== topModule)
                result.subcircuits[name] = out[name];
        }
    } else {
        result = core.yosys2digitaljs(yosysJson, options);
    }
} catch (e) {
    console.error('yosys2digitaljs conversion failed:', e);
    process.exit(1);
}

fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
console.log('Wrote', outputPath);
