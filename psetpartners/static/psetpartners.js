/*
  makeSelect functions should be called from templates with a span with id "select-id" and hidden input with id="id"
  (where the id in quotes is the value of the id argument to makeSingleSelect).

  Eventually we should migrate some of this into select-pure.js
*/

/* globals SelectPure */

function isAlphaNumeric(code) { return ( (code > 47 && code < 58) || (code > 64 || code < 91) || (code > 96 && code < 123) ); }

function addDays(d, days) { const result = new Date(d); result.setDate(result.getDate()+days); return result; }

// Functions to safely convert dates to/from YYYY-MM-DD format -- python and javascript don't play well with dates, be careful!
function fullDateToString(d) { return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function fullDateFromString(s) {
  const t = s.split('-');
  const year = parseInt(t[0]); month=parseInt(t[1])-1; day=parseInt(t[2]);
  return new Date(year,month,day,0);
  return m;
}
function makeSingleSelect(id, available, config) {
  const e = document.getElementById(id);
  if ( ! e || e.tagName != "INPUT"  ) throw 'No input element with id ' + id;
  const se = document.getElementById('select-'+id);
  if ( ! se || se.tagName != "SPAN"  ) throw 'No span element with id ' + 'select-' + id;
  function onChange(v) { if ( e.value != v ) { e.value = v; e.dispatchEvent(new Event('change')); } }
  const s = new SelectPure('#select-'+id, {
    options: available,
    value: e.value,
    onChange: onChange,
    autocomplete: config.autocomplete,
    placeholder: config.placeholder,
    notes: config.notes,
    classNames: config.classNames,
  });
  // TODO move this event handling into select-pure.js
  if ( config.autocomplete ) {
    s._autocomplete.addEventListener('keydown', function(evt) {
      if ( evt.which == 9 || evt.which == 27 ) { s.close(); se.focus(); }
    });
    se.addEventListener('keypress', function(evt) { s.open(); });
  } else {
    se.addEventListener('focusout', function(evt) { s.close(); });
  }
  se.addEventListener('keydown', function(evt) {
    if ( evt.which === 39 || evt.which === 40 ) { if ( ! s.next() ) s.open(); evt.preventDefault(); }
    else if ( evt.which === 37 || evt.which === 38 ) { if ( ! s.prev() ) s.open(); evt.preventDefault(); }
    else if ( evt.which === 27 || evt.which === 33 ) { s.close(); evt.preventDefault(); }
    else if ( evt.which === 34 ) { s.open(); evt.preventDefault(); }
    else if ( evt.which === 13 ) {  evt.preventDefault(); if ( config.autocomplete ) s.selectone(); else s.toggle(); }
  });
 
  e.value = s.value();
  jQuery(e).data('select',s);
  return s;
}

function updateSingleSelect(id, notes) {
  const e = document.getElementById(id);
  if ( ! e || e.tagName != "INPUT"  ) throw "No input element with id " + id;
  const s = jQuery(e).data('select');
  if ( !s ) throw 'Select attribute not set for input ' + id;
  if ( e.value ) s.value(e.value); else s.reset();
  if ( notes ) s.notes(notes);
}

/*
  available should be a list of { 'label': label, 'value': value } where none of the values contain commas
*/
function makeMultiSelect(id, available, config, selectClass="sp-select") {
  if ( available.find(e => e.value.includes(",")) ) throw "available values for " + id + " cannot contain commas";
  const e = document.getElementById(id);
  if ( ! e || e.tagName != "INPUT"  ) throw "No input element with id " + id;
  const se = document.getElementById('select-'+id);
  if ( ! se || se.tagName != "SPAN"  ) throw "No span element with id " + 'select-' + id;
  function onChange(v) { if ( e.value != v ) { e.value = v; e.dispatchEvent(new Event('change')); }}
  let customIcon = document.createElement('i');
  customIcon.textContent = '×'; // &times;
  let v = e.value ? e.value.trim().replace(/'/g,'"') : '';
  v = v ? JSON.parse(v) : [];
  const s = new SelectPure('#select-'+id, {
    onChange: onChange,
    options: available,
    multiple: true,
    inlineIcon: customIcon,
    autocomplete: config.autocomplete,
    value: v,
    limit: config.limit,
    onLimit: config.onLimit,
    placeholder: config.placeholder,
    shortTags: config.shortTags,
    notes: config.notes,
    select: selectClass,
    classNames: config.classNames,
  });
  // TODO move this event handling into select-pure.js
  if ( config.autocomplete ) {
    s._autocomplete.addEventListener('keydown', function(evt) {
      if ( evt.which == 9 || evt.which == 27 ) { s.close(); se.focus(); }
    });
    se.addEventListener('keypress', function(evt) { s.open(); });
  } else {
    se.addEventListener('focusout', function(evt) { s.close(); });
  }
  se.addEventListener('keydown', function(evt) {
    if ( evt.which == 34 | evt.which === 39 || evt.which === 40 || evt.which === 34 ) { s.open();  evt.preventDefault(); }
    else if ( evt.which == 33 || evt.which === 37 || evt.which === 38 || evt.which === 27 || evt.which == 33 ) { s.close();  evt.preventDefault(); }
    else if ( evt.which === 13 ) {  evt.preventDefault(); if ( config.autocomplete ) s.selectone(); else s.toggle(); }
  });
  //e.value = s.value();
  jQuery(e).data('select',s);
  return s;
}

// disable drag and drop
function disableDrag() {
  document.addEventListener('drag', function(e) { e.preventDefault(); });
  document.addEventListener('drop', function(e) { e.preventDefault(); });
  document.addEventListener('dragstart', function(e) { e.preventDefault(); });
  document.addEventListener('dragend', function(e) { e.preventDefault(); });
  document.addEventListener('dragenter', function(e) { e.preventDefault(); });
  document.addEventListener('dragover', function(e) { e.preventDefault(); });
  document.addEventListener('dragleave', function(e) { e.preventDefault(); });
}

// must be called by any code using the checkboxgrid class "cbg"
// caller must have created checkboxes with ids cb-name-i-j and spans with ids name-i-j for i=0..rows-1, j=0..cols-1 with cols > 0
function makeCheckboxGrid(name, rows, cols) {
  disableDrag();
  $('span.cbg').on('mousedown mouseup mouseover touchstart touchmove touchend', function a (e) {
    if ( typeof a.active === 'undefined' ) a.active = false;
    if ( e.type == 'mouseup' || e.type == 'touchend' || (!(e.buttons&1) && e.type == 'mouseover') ) { a.active = false; return false; }
    if ( (e.buttons&1) || e.type == 'touchstart' || e.type == 'touchmove' ) {
      const s = ('' + e.target.id).split('-'); 
      var row = s[1], col = s[2];
      if ( e.type == 'touchstart' || e.type == 'touchmove' ) { row = parseInt(row); col = parseInt(col); }
      const prefix = s[0];
      if ( e.type == 'mousedown' || e.type == 'touchstart' || (e.type == 'touchmove' && !a.active) || (e.type == 'mouseover' && !a.active) ) {
        $('#'+prefix+'-caption').focus();
        a.active = true;
        const c = document.getElementById("cb-" + e.target.id);
        a.mode = c.checked; a.row = row; a.col = col; a.prefix = prefix;
        if ( e.type == 'touchstart' || e.type == 'touchmove' ) {
          const drow = (row === 0 ? 1 : row-1), dcol = (col === 0 ? 1 : col-1);
          const d = document.getElementById(prefix+"-"+drow+"-"+dcol);
          const r1 = e.target.getBoundingClientRect(), r2 = d.getBoundingClientRect();
          a.x = r1.x; a.y = r1.y;
          a.width = Math.abs(r1.x-r2.x);
          a.height = Math.abs(r1.y-r2.y);
        }
      }
      if ( e.type == 'touchmove' ) {
        const x = e.touches[0].pageX, y = e.touches[0].pageY;
        row = a.row + (y > a.y ? Math.floor((y-a.y)/a.height) : -Math.ceil((a.y-y)/a.height));
        col = a.col + (x > a.x ? Math.floor((x-a.x)/a.width) : -Math.ceil((a.x-x)/a.width));
        if ( row < 0 ) row = 0; if ( row >= rows ) row = rows-1;
        if ( col < 0 ) col = 0; if ( col >= cols ) col = cols-1;
      }
      const srow = Math.min(a.row,row), erow = Math.max(a.row,row);
      const scol = Math.min(a.col,col), ecol = Math.max(a.col,col); 
      for ( let i = srow ; i <= erow ; i++ ) for ( let j = scol ; j <= ecol ; j++ ) {
        const t = "cb-" + a.prefix + "-" + i + "-" + j;
        const c = document.getElementById(t);
        if ( c.checked === a.mode ) { c.checked = !a.mode; c.dispatchEvent(new Event('change')); }
      }
    }
    return false;
  });
  $('span.cbg').on('click', function (e) { e.preventDefault(); });
}

function validURL(str, allow_empty=true) {
  if ( allow_empty && !str ) return true;
  const pattern = new RegExp('^https?:\\/\\/'+ // protocol (require)
    '((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|'+ // domain name
    '((\\d{1,3}\\.){3}\\d{1,3}))'+ // OR ip (v4) address
    '(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*'+ // port and path
    '(\\?[;&a-z\\d%_.~+=-]*)?'+ // query string
    '(\\#[-a-z\\d_]*)?$','i'); // fragment locator
  return !!pattern.test(str);
}

function showURLtest(id, test_id, test_anchor, errmsg) {
  const url = $('#'+id).val();
  if ( url === '' ) { $('#'+test_id).html(''); return; }
  if ( validURL(url) ) {
    $('#'+test_id).html('');
    if ( test_anchor !== '') $('#'+test_id).html('<a href="' + url + '" target="_blank">' + test_anchor + '</a>');
  } else {
    $('#'+test_id).html(errmsg);
  }
}

function makeURLtester(id, test_id, test_anchor, errmsg) {
  $('#'+id).keyup(function(evt) { evt.preventDefault(); showURLtest(id, test_id, test_anchor, errmsg);});
  showURLtest(id, test_id, test_anchor, errmsg);
}

function flashTop(msg, category) {
  const p = document.createElement('p'), pt = document.createTextNode(msg);
  const l = document.createElement('l'), lt = document.createTextNode(category=='error' ? ' [dismiss]' : ' [ok]');
  p.classList.add('flash-'+category); p.appendChild(pt); p.appendChild(l);
  l.classList.add('flash-after'); l.appendChild(lt);  l.onclick = function(e) { p.remove(); };
  document.getElementById('flash-top').appendChild(p);
}
function flashAnnounce(msg) { flashTop(msg, 'announce'); }
function flashInstruct(msg) { flashTop(msg, 'instruct'); }
function flashNotify(msg) { flashTop(msg, 'notify'); }
function flashError(msg) { flashTop(msg, 'error'); }

// TODO: We currently display only one bottom messages of each type at a time, fix this
// (there is some strange but surely easy to fix jquery issue that prevernts removing, so we reuse)

function flashInfo(msg) {
  if ( ! flashInfo.p ) {
    const p = document.createElement('p'), t = document.createTextNode(msg);
    p.classList.add('flash-info'); p.appendChild(t);
    document.getElementById('flash-bottom').appendChild(p);
    flashInfo.p = p;
  } else {
    flashInfo.p.firstChild.textContent=msg;
    jQuery(flashInfo.p).show();
  }
  jQuery(flashInfo.p).fadeOut(6000);
}

function flashWarning(msg) {
  if ( ! flashWarning.p ) {
    const p = document.createElement('p'), t = document.createTextNode(msg);
    p.classList.add('flash-warning'); p.appendChild(t);
    document.getElementById('flash-bottom').appendChild(p);
    flashWarning.p = p;
  } else {
    flashWarning.p.firstChild.textContent=msg;
    jQuery(flashWarning.p).show();
  }
  jQuery(flashWarning.p).fadeOut(6000);
}

function flashCancel(msg) {
  if ( ! flashCancel.p ) {
    const p = document.createElement('p'), t = document.createTextNode(msg);
    p.classList.add('flash-cancel'); p.appendChild(t);
    document.getElementById('flash-bottom').appendChild(p);
    flashCancel.p = p;
  } else {
    flashCancel.p.firstChild.textContent=msg;
    jQuery(flashCancel.p).show();
  }
  jQuery(flashCancel.p).fadeOut(6000);
}

window.Clipboard = (function(window, document, navigator) {
    var textArea, copy;

    function isOS() { return navigator.userAgent.match(/ipad|iphone/i); }
    function createTextArea(text) {
        textArea = document.createElement('textArea');
        textArea.value = text;
        document.body.appendChild(textArea);
    }
    function selectText() {
        if (isOS()) {
            const range = document.createRange();
            range.selectNodeContents(textArea);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            textArea.setSelectionRange(0, 999999);
        } else {
            textArea.select();
        }
    }
    function _copy() { const sts = document.execCommand('copy'); document.body.removeChild(textArea); return sts; }
    copy = function(text) { createTextArea(text); selectText(); return _copy(); };
    return { copy: copy };
})(window, document, navigator);

/* global Clipboard */
function copyToClipboard(msg) { return Clipboard.copy(msg); }
/*  const q = $('#clipboard');  // should be an input with class hidden (but not type hidden)
  q.val(msg); q.select();
  return document.execCommand('copy');*/

jQuery.extend(jQuery.expr[':'], {
  focusable: function(el, index, selector){
  return $(el).is('a, button, :input, [tabindex]');
  }
});
