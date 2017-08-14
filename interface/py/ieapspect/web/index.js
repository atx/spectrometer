/* 
 * Copyright (C) 2015-2016 Institute of Applied and Experimental Physics (http://www.utef.cvut.cz/)
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.*
 */

state = {
	histogram: null,
	binbars: null,
	binsize: 1,
	svg: null,
	cont: null,
	hist: null,
	zoom: null,
	xscale: null,
	yscale: null,
	since: 0,
	finished: null,
	threshold: 10,
	ws: null,
	cfgpropwid: {},
	autosave: null
}

function clamp(v, mi, mx) {
	if (v < mi)
		return mi;
	else if (v > mx)
		return mx;
	return v;
}

function endTime() {
	return state.finished ? state.finished : (new Date()).getTime() / 1000;
}

SIPrefixes = ["", "k", "M", "G", "T"]

function SIFormat(x) {
	x = Math.round(x);
	var i;
	for (i = 0; i < SIPrefixes.length && x > 1000; i++)
		x /= 1000;

	ret = i == 0 ? x : x.toFixed(1) + SIPrefixes[i];
	while (ret[0] == "0")
		ret = ret.substring(1);

	return ret + " ";
}

function getBarWidth() {
	return ($(state.svg[0][0]).width() / state.histogram.length * state.binsize);
}

function getBarHeight() {
	var max = d3.max(state.histogram);
	if (max == 0)
		return 10;
	return $(state.svg[0][0]).height() / max;
}

function lpad(s, t, p) {
	s = String(s);
	while (s.length < t)
		s = p + s;
	return s;
}

function updateTimer() {
	var diff = Math.round(endTime() - state.since);
	diff = Math.max(0, diff); // Should not happen, but just in case...
	var secs = diff % 60;
	var mins = Math.floor(diff / 60) % 60;
	var hrs = Math.floor(diff / 3600);
	$("#timer").text(lpad(hrs, 2, "0") + ":" + lpad(mins, 2, "0") + ":" + lpad(secs, 2, "0"));
}

function update() {
	var barw = getBarWidth();

	var binned = new Array(state.histogram.length / state.binsize).fill(0);

	for (var i = 0; i < state.histogram.length; i++) {
		if (i > state.threshold)
			binned[Math.floor(i / state.binsize)] += state.histogram[i];
	}

	var cpm = binned.reduce(function(i, v) { return i + v; }) /
		(endTime() - state.since) * 60;
	$("#cpm").text(cpm.toFixed(2) + " CPM")

	var maxh = d3.max(binned);
	var perh = maxh == 0 ? 10 : $(state.svg[0][0]).height() / maxh;

	var tickcount = 10;
	var tstep = d3.max(binned) / tickcount;
	var tvals = [0];
	for (var i = 1; i < tickcount; i++)
		tvals.push(tvals[tvals.length - 1] + tstep);

	state.xscale.range([0, barw * binned.length]);

	state.yscale.domain([d3.max(binned), 0])
				.range([0, $(state.svg[0][0]).height()]);
	var yaxis = d3.svg.axis()
					.tickValues(tvals)
					.scale(state.yscale)
					.orient("left")
					.tickFormat(SIFormat)
					.tickSize(-($(state.svg[0][0]).width() - 20))
					.outerTickSize(0);

	var xaxis = d3.svg.axis()
				.scale(state.xscale)
				.orient("top")
				.outerTickSize(0);

	state.svg.selectAll(".x.axis")
		.call(xaxis);
	state.svg.selectAll(".y.axis")
		.call(yaxis);

	for (var i = 0; i < binned.length; i++) {
		if (binned[i] > 0) {
			if (!state.binbars[i])
				state.binbars[i] = state.svg.select(".wrap").append("rect").attr("class", "bar");
			var x = state.xscale(i * state.binsize);
			var w = barw * state.zoom.scale() - Math.floor(barw * state.zoom.scale() * 0.15)
			// Beyond the edge, drop the bar entirely
			if (x + w < 0 || y > $(state.svg[0][0]).width()) {
				state.binbars[i].remove();
				state.binbars[i] = null;
				continue;
			}
			// Partially occluded, note that we don't care about occlusion
			// on the right border, as there are no axis we could be covering
			if (x < 0) {
				w = w + x;
				x = 0;
			}
			var y = Math.floor(state.yscale(binned[i]))
			var h = Math.floor(binned[i] * perh)
			state.binbars[i].data([{
				x: x,
				w: w,
				y: y,
				h: h,
			}]);
		} else if (state.binbars[i]) {
			state.binbars[i].remove();
			state.binbars[i] = null;
		}
	}

	var bs = state.svg.selectAll(".bar");

	bs.attr("width", function(d) { return d.w; })
		.attr("x", function(d) { return d.x; });

	bs.attr("height", function(d) { return d.h + "px"; })
		.attr("y", function(d) { return d.y; });

	d3.select(".pane")
		.attr("width", $(state.svg[0][0]).width() + "px")
		.attr("height", $(state.svg[0][0]).height() + "px");
}

function commandSender(cmd) {
	return function () { state.ws.send(JSON.stringify({"command": cmd}))}
}

function download(fname, data) {
	var el = document.createElement("a");
	el.setAttribute("download", fname)
	el.setAttribute("href", "data:text/html:charset=utf-8," +
								encodeURIComponent(data));
	el.style.display = "none";
	document.body.appendChild(el);
	el.click();
	document.body.removeChild(el);
}

function downloadTXT() {
	var startlabel = (new Date(state.since * 1000)).toISOString()
	var data = "-_-\n";
	data += "from: " + startlabel + "\n";
	data += "to: " + (new Date(endTime() * 1000)).toISOString() + "\n";
	data += "---\n";
	for (var i = 0; i < state.histogram.length; i++) {
		data += state.histogram[i] + "\n";
	}
	download("data-" + startlabel.substring(0, 19) + ".txt", data);
}

function init() {
	state.svg = d3.select("body").append("svg");

	state.xscale = d3.scale.linear()
			.domain([0, state.histogram.length])
			.range([0, getBarWidth() * state.histogram.length]);
	state.yscale = d3.scale.linear();

	state.zoom = d3.behavior.zoom().x(state.xscale).center(null)
				.scaleExtent([1, 100]).on("zoom", function() {
		var tr = state.zoom.translate();
		var tx = tr[0];

		tx = clamp(tx,
				getBarWidth() * state.histogram.length / state.binsize -
				$(state.svg[0][0]).width() * state.zoom.scale(), 0);

		state.zoom.translate([tx, tr[1]]);

		update();
	});

	state.svg.append("g").attr("class", "y axis");
	state.svg.append("g").attr("class", "x axis");

	state.cont = state.svg.append("g").attr("class", "wrap");
	state.hist = state.cont.selectAll(".bar");

	// Needs to be on the end (top)
	state.svg.append("rect")
		.attr("class", "pane")
		.call(state.zoom);

	state.binsize = $("#binsize").val();
	$("#binsize").change(function() {
		state.binsize = $("#binsize").val();

		state.svg.selectAll(".bar").remove();

		state.binbars = new Array(state.histogram.length / state.binsize).fill(null);
		update();
	}).trigger("change");
	$("#threshold").change(function() {
		state.threshold = $(this).val();
		update();
	}).trigger("change");
	$("#csv").click(downloadTXT);
	$("#autosave").change(function(ev) {
		clearInterval(state.autosave);
		var v = parseInt($(ev.target).val());
		if (isNaN(v)) {
			state.autosave = null;
		} else {
			setInterval(function() {
				downloadTXT();
				commandSender("clear")();
			}, v * 1000);
		}
	});
}

function initRemote(data) {
	data["configprops"].forEach(function (c, i) {
		var id = "config-" + c.id;
		$("<label for=" + id + ">" + c.name + "</label>").appendTo("#control");
		if (c.from == 0 && c.to == 1) {
			var ctl = $("<input type=\"checkbox\" id=\"" + id + "\"></input>").appendTo("#control");
		} else {
			var ctl = $("<input type=\"number\" id=\"" + id + "\" min=" + c.from + " max=" + c.to + ">")
				.appendTo("#control");
		}
		ctl.change(function() {
			state.ws.send(JSON.stringify({"command": "set", "id": c.id,
											"value": this.value == "on" ?
														(this.checked ? 1 : 0) :
														parseInt(this.value)}));
		})
		state.cfgpropwid[c.id] = ctl;
	});
	$("#download").click(function () {
		var stored =
			$("<div id=\"stored\"></div>")
				.appendTo($("body"))
				.css("display", "none")
				.html(JSON.stringify(
							{hist: state.histogram,
							 since: state.since,
							 finished: (new Date()).getTime / 1000}));

		// Save the current binsize
		$("#binsize option:selected").attr("selected", true);

		download("spectrum.html", document.documentElement.innerHTML);

		stored.remove();
	})
	$("#clear").click(commandSender("clear"));

	setInterval(update, 100);
	setInterval(updateTimer, 1000);
	$("#clear").attr("disabled", null);

	state.ws = new WebSocket("ws://" + location.hostname + ":" + location.port + "/ws");
	state.ws.onopen = function() {
		state.ws.send(JSON.stringify({"csrf": data["csrf"]}));
	}
	state.ws.onmessage = function(msg) {
		var d = $.parseJSON(msg.data);
		if (d.v) {
			state.histogram[d.v] += 1;
		} else if (d.c) {
			console.log("Config received!");
		} else if (d.h) {
			console.log("History received!");
			state.histogram = d.h;
			state.since = d.since;
		} else if (d.props) {
			console.log("Configuration properties received!");
			for (var k in d.props) {
				var el = state.cfgpropwid[k];
				if (el.prop("type") == "checkbox") {
					el.prop("checked", !!d.props[k]);
				} else {
					el.val(d.props[k]);
				}
			}
		} else {
			console.log("WTF? " + d);
		}
	}
}

$(document).ready(function() {
	var stored = $("#stored");
	if (stored.length) {
		$("svg").remove();
		var sdata = JSON.parse(stored.html());
		state.histogram = sdata.hist;
		state.since = sdata.since;
		state.finished = sdata.finished;
		init();
		$(["#clear"]).each(function(i, v) {
			$(v).prop("disabled", true);
		});
		update();
	} else {
		$.get("metadata.json", function(data) {
			state.histogram = new Array(data["channels"]).fill(1);
			init();
			initRemote(data);
		})
	}
})
