var selectPureClassNames = {
  select: "select-pure__select",
  dropdownShown: "select-pure__select--opened",
  multiselect: "select-pure__select--multiple",
  label: "select-pure__label",
  placeholder: "select-pure__placeholder",
  dropdown: "select-pure__options",
  option: "select-pure__option",
  autocompleteInput: "select-pure__autocomplete",
  selectedLabel: "select-pure__selected-label",
  selectedOption: "select-pure__option--selected",
  placeholderHidden: "select-pure__placeholder--hidden",
  optionHidden: "select-pure__option--hidden",
};

/*
  makeSelect functions should be called from templates with a span with id "select-id" and hidden input with id="id"
  (where the id in quotes is the value of the id argument to makeSingleSelect).
*/
function makeSingleSelect (id, available, reset=false, auto=false) {
  const e = document.getElementById(id);
  if ( ! e || e.tagName != "INPUT"  ) throw "No input element with id " + id;
  const se = document.getElementById('select-'+id);
  if ( ! se || se.tagName != "SPAN"  ) throw "No span element with id " + 'select-' + id;
  function onchange(v) {
    v = v.trim();
    if ( reset && v === resetOptionValue ) v = '';  //  resetOptionValue = "__reset__" is defined in options.js
    if ( e.value != v ) {
        e.value = v;
        if ( ! v ) jQuery(e).data('select').reset();
        e.dispatchEvent(new Event('change'));
    }
  }
  const s = new SelectPure('#select-'+id, { options: available, value: e.value, onChange: onchange, autocompute: auto});
  se.addEventListener('keydown', function(evt) { if (evt.which === 40) selectNextOption(id); if (evt.which === 38) selectPrevOption(id); });
  se.addEventListener('focusout', function(evt) { selectClose(s); });
  e.value = s.value();
  jQuery(e).data('select',s);
  return s;
}

function selectClose(s) {
  if (s._state.opened) {
    console.log("closing");
    s._select.removeClass(s._config.classNames.dropdownShown);
    s._body.removeEventListener("click", s._boundHandleClick);
    s._select.addEventListener("click", s._boundHandleClick);
    s._state.opened = false;
  }
}

function selectNextOption (id) {
  const s = jQuery(document.getElementById(id)).data('select');
  if ( s._config.multiple ) return false;
  let i = s._config.options.findIndex(x => x.value === s._config.value);
  if ( i === s._config.options.length-1 ) return false;
  if ( i === -1 && s._config.options[0].value === resetOptionValue ) i=0;
  s._setValue(s._config.options[i+1]['value'], true);
  return true;
}

function selectPrevOption (id) {
  const s = jQuery(document.getElementById(id)).data('select');
  if ( s._config.multiple ) return false;
  i = s._config.options.findIndex(x => x.value === s._config.value);
  if ( i < 1 ) return false;
  v = s._config.options[i-1]['value'];
  s._setValue(s._config.options[i-1]['value'], true);
  return true;
}

/*
  available should be a list of { 'label': label, 'value': value } where none of the values contain commas
*/
function makeMultiSelect(id, available, auto=false, short=false) {
  if ( available.find(e => e.value.includes(",")) ) throw "available values cannot contain commas";
  const e = document.getElementById(id);
  if ( ! e || e.tagName != "INPUT"  ) throw "No input element with id " + id;
  const se = document.getElementById('select-'+id);
  if ( ! se || se.tagName != "SPAN"  ) throw "No span element with id " + 'select-' + id;
  function onchange(v) { if ( e.value != v ) { e.value = v; e.dispatchEvent(new Event('change')); }}
  var customIcon = document.createElement('i');
  customIcon.textContent = '×'; // &times;
  const s = new SelectPure('#select-'+id, {
    onChange: onchange,
    options: available,
    multiple: true,
    autocomplete: auto,
    inlineIcon: customIcon,
    value: eval(e.value),
    shortlabels: short,
    classNames: selectPureClassNames,
  });
  if ( auto ) {
    s._autocomplete.addEventListener('keydown', function(evt) { if (evt.which==9) { selectClose(s); se.focus(); }});
  } else {
    se.addEventListener('focusout', function(evt) { selectClose(s); });
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
