ace.define("ace/mode/phcmu_config_highlight_rules",["require","exports","module","ace/lib/oop","ace/mode/text_highlight_rules"], function(require, exports, module){

"use strict";

var oop = require("../lib/oop");
var TextHighlightRules = require("./text_highlight_rules").TextHighlightRules;

var PhcmuConfigHighlightRules = function () {
    var keywords = ("AND|OR|OF|POINTS|POINT|HINTS|HINT|EVERY|MINUTES|MINUTE|HOURS|HOUR|SOLVE|UNLOCK|AFTER|IF");
    var keywordMapper = this.createKeywordMapper({"keyword": keywords}, "identifier", true);
    this.$rules = {
        "start": [{
                token: "comment",
                regex: "#.*"
            }, {
                token: ["keyword", "constant.numeric", "keyword"],
                regex: "(EVERY)(\\s+\\d+\\s+)((?:MINUTES?|HOURS?))",
                caseInsensitive: true
            }, {
                token: ["keyword", "constant.language", "keyword"],
                regex: "((?:P\\w+)\\s+)(SOLVE|UNLOCK)\\b",
                caseInsensitive: true
            }, {
                token: "constant.language",
                regex: "[Pp](?:[a-fA-F0-9]+|[Xx])\\b",
            }, {
                token: "constant.language",
                regex: "\\+\\d?\\d:\\d\\d\\b",
            }, {
                token: "constant.numeric",
                regex: "\\d+(?=\\s*(?:POINTS?|HINTS?)\\b)",
            }, {
                token : keywordMapper,
                regex : "[a-zA-Z]+\\b"
            }, {
                token : "paren.lparen",
                regex : "[\\[\\(]"
            }, {
                token : "paren.rparen",
                regex : "[\\]\\)]"
            }, {
                token : "keyword.operator",
                regex : "<=",
            }, {
                token: "text",
                regex: "\\s+"
            }],
    };
};
oop.inherits(PhcmuConfigHighlightRules, TextHighlightRules);
exports.PhcmuConfigHighlightRules = PhcmuConfigHighlightRules;

});

ace.define("ace/mode/phcmu_config",["require","exports","module","ace/lib/oop","ace/mode/text","ace/mode/phcmu_config_highlight_rules","ace/range"], function(require, exports, module){"use strict";
var oop = require("../lib/oop");
var TextMode = require("./text").Mode;
var PhcmuConfigHighlightRules = require("./phcmu_config_highlight_rules").PhcmuConfigHighlightRules;
var Range = require("../range").Range;
var Mode = function () {
    this.HighlightRules = PhcmuConfigHighlightRules;
    this.$behaviour = this.$defaultBehaviour;
};
oop.inherits(Mode, TextMode);

(function () {
    this.$id = "ace/mode/phcmu_config";
}).call(Mode.prototype);
exports.Mode = Mode;

});

(function() {
    ace.require(["ace/mode/phcmu_config"], function(m) {
        if (typeof module == "object" && typeof exports == "object" && module) {
            module.exports = m;
        }
    });
})();
            