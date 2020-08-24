/*
  makeSelect functions should be called from templates with a span with id "select-id" and hidden input with id="id"
  (where the id in quotes is the value of the id argument to makeSingleSelect).

  Eventually we should migrate some of this into select-pure.js
*/

/* globals SelectPure */

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
  });
  se.addEventListener('keydown', function(evt) {
    if ( evt.which === 39 || evt.which === 40 ) { if ( ! s.next() ) s.open(); }
    else if ( evt.which === 37 || evt.which === 38 ) { if ( ! s.prev() ) s.open(); }
    else if ( evt.which === 27 ) s.close();
  });
  se.addEventListener('focusout', function(evt) { s.close(); });
  e.value = s.value();
  jQuery(e).data('select',s);
  return s;
}

function updateSingleSelect(id, notes) {
  const e = document.getElementById(id);
  if ( ! e || e.tagName != "INPUT"  ) throw "No input element with id " + id;
  const s = jQuery(e).data('select');
  if ( !s ) throw 'Select attribute not set for in put ' + id;
  if ( e.value ) s.value(e.value); else s.reset();
  if ( notes ) s.notes(notes);
}

/*
  available should be a list of { 'label': label, 'value': value } where none of the values contain commas
*/
function makeMultiSelect(id, available, config) {
  if ( available.find(e => e.value.includes(",")) ) throw "available values cannot contain commas";
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
  });
  if ( config.autocomplete ) {
    s._autocomplete.addEventListener('keydown', function(evt) {
      if ( evt.which == 9 || evt.which == 27 ) { s.close(); se.focus(); }
    });
  } else {
    se.addEventListener('keydown', function(evt) {
      if ( evt.which === 39 || evt.which === 40 ) s.open();
      else if ( evt.which === 37 || evt.which === 38 || evt.which === 27 ) s.close();
    });
    se.addEventListener('focusout', function(evt) { s.close(); });
  }
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
function makeCheckboxGrid(name,rows,cols) {
  disableDrag();
  $('span.cbg').on('mousedown mouseup mouseover', function a (e) {
    if ( typeof a.active === 'undefined' ) a.active = false;
    if ( e.type == 'mouseup' || (!(e.buttons&1) && e.type == 'mouseover') ) { a.active = false; return false; }
    if ( e.buttons&1 ) {
      const s = ('' + e.target.id).split('-'); 
      const row = s[1], col = s[2], prefix = s[0];
      if ( e.type == 'mousedown' || (e.type == 'mouseover' && !a.active) ) {
         a.active = true;
         const c = document.getElementById("cb-" + e.target.id);
         a.mode = c.checked; a.row = row; a.col = col; a.prefix = prefix;
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
