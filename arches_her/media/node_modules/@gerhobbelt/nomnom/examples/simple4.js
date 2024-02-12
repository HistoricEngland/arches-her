// run as:
//
//    node examples/simple4.js  build --help
//

var Parser = require("../nomnom");

var version = "SAMPLE v1.0.1";

var parser = new Parser();
parser
    .script("runtests")
    .nocommand()
    .options({
        version: {
            flag: true,
            help: 'print version and exit',
            callback: function show_version() {
                console.log('exec callback...\n');
                return `version ${version}`;
            }
        }
    })
    .callback(cbcb);

parser
    .command('build')
    .options({
        path: {
            position: 0,
            help: "Test file to run",
            list: true
        },
        config: {
            abbr: 'c',
            metavar: 'FILE',
            help: "Config file with tests to run"
        },
        debug: {
            abbr: 'd',
            flag: false,
            optional: true,
            default: 0,
            help: "Print debugging info"
        },
    })
    .option('config', {
        abbr: 'c',
        'default': 'config.json',
        help: 'JSON file with configuration settings'
    })
    .callback(cbcb)
    .help('build from sources');


var opts = parser.parse();

//console.log('\nMAIN opts:\n', JSON.stringify(opts, undefined, 4));
console.log('\n-- The END. --\n');


function cbcb(opts, cmd) {
    console.log('\nopts:\n', JSON.stringify(opts, undefined, 4));
    console.log('cmd:\n', JSON.stringify(cmd, undefined, 4));
}
