// Mode Peneliti: cascaded classifier picker (variant -> feature type -> feature code -> algorithm), Alpine.js.
// Every option comes from the server's model catalog (json_script "classifier-catalog"); the chosen catalog id goes
// into the hidden `classifier_id` input, which the server validates against the same catalog (whitelist).
document.addEventListener("alpine:init", function () {
  window.Alpine.data("classifierPicker", function (initialId) {
    var source = document.getElementById("classifier-catalog");
    var catalog = JSON.parse(source ? source.textContent : '{"entries": []}');
    var entries = catalog.entries || [];
    var start = entries.find(function (e) { return e.id === initialId && e.available; }) ||
      entries.find(function (e) { return e.id === catalog.defaultId; }) || entries[0] || {};

    function soon(text, available) {
      return available ? text : text + " (" + catalog.text.comingSoon + ")";
    }

    function pick(options, current) {
      var keep = options.find(function (o) { return o.id === current && o.available; });
      if (keep) return current;
      var first = options.find(function (o) { return o.available; });
      return first ? first.id : current;
    }

    return {
      catalog: catalog,
      variant: start.variant,
      featureType: start.featureType,
      codes: start.codes,
      algorithm: start.algorithm,

      init: function () {
        var self = this;
        ["variant", "featureType", "codes"].forEach(function (level) {
          self.$watch(level, function () { self.normalize(); });
        });
      },

      // Keep every lower level on a valid, available option after a higher level changes.
      normalize: function () {
        this.featureType = pick(this.featureTypeOptions, this.featureType);
        this.codes = pick(this.codesOptions, this.codes);
        this.algorithm = pick(this.algorithmOptions, this.algorithm);
      },

      filtered: function (levels) {
        var self = this;
        return entries.filter(function (e) {
          return levels.every(function (level) { return e[level] === self[level]; });
        });
      },

      get variantOptions() {
        return (catalog.variants || []).map(function (v) {
          var ok = entries.some(function (e) { return e.variant === v.id && e.available; });
          return { id: v.id, available: ok, text: soon(v.label, ok) };
        });
      },

      get featureTypeOptions() {
        var list = this.filtered(["variant"]);
        return (catalog.featureTypes || []).filter(function (t) {
          return list.some(function (e) { return e.featureType === t.id; });
        }).map(function (t) {
          var ok = list.some(function (e) { return e.featureType === t.id && e.available; });
          return { id: t.id, available: ok, text: soon(t.label, ok) };
        });
      },

      get codesOptions() {
        var seen = [];
        var list = this.filtered(["variant", "featureType"]);
        list.forEach(function (e) { if (seen.indexOf(e.codes) < 0) seen.push(e.codes); });
        return seen.map(function (code) {
          var ok = list.some(function (e) { return e.codes === code && e.available; });
          return { id: code, available: ok, text: soon(code, ok) };
        });
      },

      get algorithmOptions() {
        return this.filtered(["variant", "featureType", "codes"]).map(function (e) {
          var parts = [e.algorithmLabel, catalog.text.f1Cv + " " + e.f1Cv, catalog.text.f1Test + " " + e.f1Test];
          return { id: e.algorithm, available: e.available, text: parts.concat(e.tags).join(" · ") };
        });
      },

      get entry() {
        return this.filtered(["variant", "featureType", "codes", "algorithm"])[0] || null;
      },

      get selectedId() {
        var entry = this.entry;
        return entry ? entry.id : "";
      },

      get title() {
        var entry = this.entry;
        if (!entry) return "";
        var type = (catalog.featureTypes || []).find(function (t) { return t.id === entry.featureType; });
        return [entry.variant.toUpperCase(), type ? type.label : "", entry.codes, entry.algorithmName].join(" · ");
      },

      get variantNote() {
        var self = this;
        var v = (catalog.variants || []).find(function (item) { return item.id === self.variant; });
        return v ? v.description : "";
      },

      get featureNotes() {
        var entry = this.entry;
        if (!entry) return [];
        return entry.codes.split("+").map(function (code) {
          return code + ": " + (catalog.features[code] || "");
        });
      },
    };
  });
});
