// Shared data + helpers for every World Pulse globe (hero + logo) on every page.
window.WorldPulseGlobe = (function () {
  const DENSITY = {"Afghanistan":62,"Albania":98,"Algeria":19,"Angola":26,"Antarctica":0,"Argentina":17,"Armenia":102,"Australia":3.3,"Austria":109,"Azerbaijan":123,"Bahamas":39,"Bangladesh":1265,"Belarus":45,"Belgium":383,"Belize":17,"Benin":115,"Bhutan":21,"Bolivia":11,"Bosnia and Herz.":60,"Botswana":4,"Brazil":25,"Brunei":83,"Bulgaria":62,"Burkina Faso":79,"Burundi":463,"Cambodia":96,"Cameroon":58,"Canada":4.2,"Central African Rep.":8,"Chad":14,"Chile":26,"China":149,"Colombia":46,"Congo":17,"Costa Rica":100,"Croatia":68,"Cuba":100,"Cyprus":130,"Czechia":139,"Côte d'Ivoire":84,"Dem. Rep. Congo":44,"Denmark":138,"Djibouti":43,"Dominican Rep.":227,"Ecuador":71,"Egypt":105,"El Salvador":305,"Eq. Guinea":51,"Eritrea":34,"Estonia":30,"Ethiopia":115,"Falkland Is.":0.3,"Fiji":49,"Finland":18,"Fr. S. Antarctic Lands":0,"France":119,"Gabon":9,"Gambia":232,"Georgia":64,"Germany":240,"Ghana":141,"Greece":80,"Greenland":0.03,"Guatemala":158,"Guinea":54,"Guinea-Bissau":70,"Guyana":4,"Haiti":414,"Honduras":90,"Hungary":105,"Iceland":3.7,"India":464,"Indonesia":151,"Iran":53,"Iraq":96,"Ireland":73,"Israel":400,"Italy":196,"Jamaica":267,"Japan":336,"Jordan":117,"Kazakhstan":7,"Kenya":94,"Kosovo":159,"Kuwait":240,"Kyrgyzstan":35,"Laos":32,"Latvia":29,"Lebanon":550,"Lesotho":73,"Liberia":55,"Libya":4,"Lithuania":42,"Luxembourg":260,"Macedonia":82,"Madagascar":48,"Malawi":208,"Malaysia":99,"Mali":18,"Mauritania":4.7,"Mexico":66,"Moldova":89,"Mongolia":2.1,"Montenegro":46,"Morocco":84,"Mozambique":40,"Myanmar":82,"N. Cyprus":100,"Namibia":3.1,"Nepal":203,"Netherlands":508,"New Caledonia":15,"New Zealand":19,"Nicaragua":56,"Niger":21,"Nigeria":226,"North Korea":214,"Norway":15,"Oman":17,"Pakistan":287,"Palestine":847,"Panama":58,"Papua New Guinea":20,"Paraguay":18,"Peru":27,"Philippines":368,"Poland":122,"Portugal":111,"Puerto Rico":350,"Qatar":227,"Romania":80,"Russia":8.8,"Rwanda":525,"S. Sudan":18,"Saudi Arabia":16,"Senegal":89,"Serbia":78,"Sierra Leone":111,"Slovakia":113,"Slovenia":103,"Solomon Is.":24,"Somalia":26,"Somaliland":25,"South Africa":49,"South Korea":527,"Spain":94,"Sri Lanka":342,"Sudan":25,"Suriname":3.7,"Sweden":26,"Switzerland":219,"Syria":118,"Taiwan":673,"Tajikistan":70,"Tanzania":70,"Thailand":137,"Timor-Leste":89,"Togo":158,"Trinidad and Tobago":273,"Tunisia":79,"Turkey":111,"Turkmenistan":13,"Uganda":216,"Ukraine":66,"United Arab Emirates":118,"United Kingdom":281,"United States of America":36,"Uruguay":20,"Uzbekistan":82,"Vanuatu":26,"Venezuela":32,"Vietnam":314,"W. Sahara":2.2,"Yemen":56,"Zambia":26,"Zimbabwe":38,"eSwatini":67};

  function densityColor(v) {
    const stops = [
      [0,   [59,130,246]],
      [10,  [6,182,212]],
      [50,  [132,204,22]],
      [120, [234,179,8]],
      [300, [249,115,22]],
      [700, [239,68,68]],
    ];
    let lo = stops[0], hi = stops[stops.length - 1];
    for (let i = 0; i < stops.length - 1; i++) {
      if (v >= stops[i][0] && v <= stops[i+1][0]) { lo = stops[i]; hi = stops[i+1]; break; }
      if (v > stops[stops.length-1][0]) { lo = hi = stops[stops.length-1]; }
    }
    const span = hi[0] - lo[0] || 1;
    const t = Math.max(0, Math.min(1, (v - lo[0]) / span));
    const r = Math.round(lo[1][0] + (hi[1][0]-lo[1][0]) * t);
    const g = Math.round(lo[1][1] + (hi[1][1]-lo[1][1]) * t);
    const b = Math.round(lo[1][2] + (hi[1][2]-lo[1][2]) * t);
    return `rgb(${r},${g},${b})`;
  }

  let countriesPromise = null;
  function loadCountries() {
    if (!countriesPromise) {
      countriesPromise = fetch('/data/world-110m.json')
        .then(r => r.json())
        .then(topo => topojson.feature(topo, topo.objects.countries).features);
    }
    return countriesPromise;
  }

  return { DENSITY, densityColor, loadCountries };
})();
