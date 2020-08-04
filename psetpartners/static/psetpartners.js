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
  makeSelect functions should be called from templates with a span and hidden input with name="name".
*/
function makeSingleSelect (name, available, selected, reset=false, auto=false) {
  const q = 'input[name="' + name + '"]';
  const reset_value = '__reset__';
  if ( reset ) available.unshift({label: '', value:' __reset__'});
  function onchange(v) {
    v = v.trim();
    if ( reset && v == reset_value ) v = '';
    if ( $(q).val() != v ) {
        $(q).data('oldvalue', $(q).val());
        if ( ! v ) $(q).data('select').reset();
        $(q).val(v);
        $(q)[0].dispatchEvent(new Event('change'));
    }
  }
  const s = new SelectPure('span[name="' + name + '"]', { options: available, value: selected, onChange: onchange, autocompute: auto});
  $(q).data('select',s);
  return s;
}

function makeMultiSelect(name, available, selected, auto=false, short=false) {
  const q = 'input[name="' + name + '"]';
  function onchange(v) {
    if ( $(q).val() != v ) { $(q).val(v); $(q)[0].dispatchEvent(new Event('change')); }
  }
  const s = new SelectPure('span[name="' + name + '"]', {
    onChange: onchange,
    options: available,
    multiple: true,
    autocomplete: auto,
    icon: "fa fa-times",
    inlineIcon: false,
    value: selected,
    shortlabels: short,
    classNames: selectPureClassNames,
  });
  $(q).val(s.value());
  $(q).data('select',s);
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

// must be called by any code using the checkboxgrid class
function makeCheckboxGrid(name,rows,cols) {
  disableDrag();
  $('span.checkboxgrid').on('mousedown mouseup mouseover', function a (e) {
    if ( typeof a.active === 'undefined' ) a.active = false;
    if ( e.type == 'mouseup' || (!(e.buttons&1) && e.type == 'mouseover') ) { a.active = false; return false; }
    if ( e.buttons&1 ) {
       const s = ('' + e.target.id).split('-'); 
       row = s[1]; col = s[2]; prefix = s[0];
       if ( e.type == 'mousedown' || (e.type == 'mouseover' && !a.active) ) {
         a.active = true;
         c = document.getElementById("check-" + e.target.id);
         a.mode = c.checked; a.row = row; a.col = col; a.prefix = prefix;
       }
       const srow = Math.min(a.row,row), erow = Math.max(a.row,row);
       const scol = Math.min(a.col,col), ecol = Math.max(a.col,col); 
       for ( let i = srow ; i <= erow ; i++ ) for ( let j = scol ; j <= ecol ; j++ ) {
         t = "check-" + a.prefix + "-" + i + "-" + j;
         c = document.getElementById(t);
         c.checked = !a.mode;
       }
       c.dispatchEvent(new Event('change'));
    }
    return false;
  });
  $('span.checkboxgrid').on('click', function (e) { e.preventDefault(); });
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
