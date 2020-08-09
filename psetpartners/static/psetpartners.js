/*
  makeSelect functions should be called from templates with a span with id "select-id" and hidden input with id="id"
  (where the id in quotes is the value of the id argument to makeSingleSelect).

  Eventually we should migrate some of this into select-pure.js
*/
function makeSingleSelect (id, available, config) {
  const e = document.getElementById(id);
  if ( ! e || e.tagName != "INPUT"  ) throw "No input element with id " + id;
  const se = document.getElementById('select-'+id);
  if ( ! se || se.tagName != "SPAN"  ) throw "No span element with id " + 'select-' + id;
  function onChange(v) {
    v = v.trim();
    if ( config.resetOption && v === resetOptionValue ) v = '';  //  resetOptionValue = "__reset__" is defined in options.js
    if ( e.value != v ) {
        e.value = v;
        if ( ! v ) jQuery(e).data('select').reset();
        e.dispatchEvent(new Event('change'));
    }
  }
  const s = new SelectPure('#select-'+id, {
    options: available,
    value: e.value,
    onChange: onChange,
    autocomplete: config.autocomplete,
  });
  se.addEventListener('keydown', function(evt) {
    if ( evt.which === 40 ) s.next();
    if ( evt.which === 38 ) s.prev();
    if ( evt.which === 27 ) s.close();
  });
  se.addEventListener('focusout', function(evt) { s.close(); });
  e.value = s.value();
  jQuery(e).data('select',s);
  return s;
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
  var customIcon = document.createElement('i');
  customIcon.textContent = '×'; // &times;
  const s = new SelectPure('#select-'+id, {
    limit: config.limit,
    onLimit: config.onLimit,
    onChange: onChange,
    options: available,
    multiple: true,
    autocomplete: config.autocomplete,
    inlineIcon: customIcon,
    value: eval(e.value),
    shortTags: config.shortTags,
  });
  if ( config.autocomplete ) {
    s._autocomplete.addEventListener('keydown', function(evt) {
      if ( evt.which == 9 || evt.which == 27 ) { selectClose(s); se.focus(); }
    });
  } else {
    se.addEventListener('keydown', function(evt) {
      if ( evt.which === 40 ) s.open();
      if ( evt.which === 38 || evt.which === 27 ) s.close();
    });
    se.addEventListener('focusout', function(evt) { s.close(); });
  }
  e.value = s.value();
  jQuery(e).data('select',s);
  return s;
}

// removes the most recently selected item of the named multi-select, if any
// this can be used to enforce an upper limit on the number of selected items
// (won't trigger a change by default so safe to call from within change event handler)
function trimMultiSelect(id, limit, change=false) {
  const s = jQuery(document.getElementById(id)).data('select');
  let v = s.value();
  if ( limit < 1 || v.length <= limit ) return false;
  selectClose(s);
  while ( v.length > limit ) v.pop();
  s._setValue(v, change, true);
  return true;
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
       row = s[1]; col = s[2]; prefix = s[0];
       if ( e.type == 'mousedown' || (e.type == 'mouseover' && !a.active) ) {
         a.active = true;
         c = document.getElementById("cb-" + e.target.id);
         a.mode = c.checked; a.row = row; a.col = col; a.prefix = prefix;
       }
       const srow = Math.min(a.row,row), erow = Math.max(a.row,row);
       const scol = Math.min(a.col,col), ecol = Math.max(a.col,col); 
       for ( let i = srow ; i <= erow ; i++ ) for ( let j = scol ; j <= ecol ; j++ ) {
         t = "cb-" + a.prefix + "-" + i + "-" + j;
         c = document.getElementById(t);
         c.checked = !a.mode;
       }
       c.dispatchEvent(new Event('change'));
    }
    return false;
  });
  $('span.cbg').on('click', function (e) { e.preventDefault(); });
}

function validURL(str) {
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
  if ( url == '' ) { $('#'+test_id).html(''); return; }
  if ( validURL(url) ) {
    $('#'+test_id).html('');
    if ( test_anchor != '') $('#'+test_id).html('<a href="' + url + '" target="_blank">' + test_anchor + '</a>');
  } else {
    $('#'+test_id).html(errmsg);
  }
}

function makeURLtester(id, test_id, test_anchor, errmsg) {
  $('#'+id).keyup(function(evt) { evt.preventDefault(); url_tester(id, test_id, test_anchor, errmsg);});
  url_tester(id, test_id, test_anchor, errmsg);
}
