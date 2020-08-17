const allowedAttributes = { value: "data-value", disabled: "data-disabled", class: "class", type: "type" };

class Element {
  constructor(element, attributes = {}, i18n = {}) {
    this._node = element instanceof HTMLElement ? element : document.createElement(element);
    this._config = { i18n };
    this._setAttributes(attributes);
    if (attributes.textContent) this._setTextContent(attributes.textContent);
    return this;
  }

  get() { return this._node; }
  append(element) { this._node.appendChild(element); return this; }
  addClass(className) { this._node.classList.add(className); return this; }
  removeClass(className) { this._node.classList.remove(className); return this; }
  toggleClass(className) { this._node.classList.toggle(className); return this; }
  addEventListener(type, callback) { this._node.addEventListener(type, callback); return this; }
  removeEventListener(type, callback) { this._node.removeEventListener(type, callback); return this; }
  setText(text) { this._setTextContent(text); return this; }
  getHeight() { return window.getComputedStyle(this._node).height; }
  setTop(top) { this._node.style.top = `${top}px`; return this; }
  focus() { this._node.focus(); return this; }
  _setTextContent(textContent) { this._node.textContent = textContent; }
  _setAttributes(attributes) {
    for (const key in attributes) if (allowedAttributes[key] && attributes[key]) this._setAttribute(allowedAttributes[key], attributes[key]);
  }
  _setAttribute(key, value) { this._node.setAttribute(key, value); }
}

const CLASSES = {
  select: "sp-select",                          // container div for select
  focus: "sp-focus",                            // class added to select when parent has the focus
  multiselect: "sp-multiselect",                // added to container div for multiselect
  selectOpen: "sp-select-open",                 // class added to container div when dropdown is open
  dropdown: "sp-dropdown",                      // container div for dropdown list
  label: "sp-label",                            // span showing selected option (or tags) in select div
  tag: "sp-tag",                                // span for tag correspdoning to a selected option in multiselect div
  placeholder: "sp-placeholder",                // placeholder span, can used to show open-arrow (use ::after with absolute positioning)
  placeholderHidden: "sp-placeholder-hidden",   // class added to placeholder once an option is set
  option: "sp-option",                          // div for each option in dropdown list
  optionDisabled: "sp-option-disabled",         // class added to option when disabled
  optionHidden: "sp-option-hidden",             // class added to option when hidden
  optionSelected: "sp-option-selected",         // class added to option when selected
  autocompleteInput: "sp-autocomplete",         // text box for autocomplete input
};

/*
  SelectPure(element, config)

  element should be a span (this determines where the selector will appear on your form)

  required config args:
     options : an array of objects with string properties "value", "label", and optional boolean "disabled"
  
  optional config args:
     multiple: boolean (allows selection of multiple options, including no options)
     value: string or array of strings (depending on multiple) giving initial value
     onChange: function (called whenever selection changes)
     placeholder: string (placeholder shown when no options are selected if multiple is set)
     autocomplete : boolean (enables autocomplete text input for selecting options)
     shortTags: boolean (use values rather than labels for selected option tags if multiple is set)
     limit: integer (maximum number of selected options allowed, relevant only if multiple is set)
     onLimit: function (called when user attempts to exceed limit if multiple is set)
     classNames: object (use to override default class names in CLASSES)
     inlineIcon: element (icon shown in multiselect tags to allow unselecting)
     icon: string (classes of <i> eleements for multiselect tag icons when inlineIcon is not set, e.g. "fa fa-times")
*/
class SelectPure {
  constructor(element, config) {
    // the line below will upset jshint (which only seems to understand esversion 6), comment out to lint
    this._config = { ...config, classNames: { ...CLASSES, ...config.classNames }, disabledOptions: [] };
    this._state = { opened: false };
    this._icons = [];
    if ( this._config.autocomplete ) this._boundNarrowOptions = this._narrowOptions.bind(this);
    if ( this._config.multiple ) {
      this._boundHandleClick = this._handleClickMultiple.bind(this);
      this._boundUnselectOption = this._unselectOption.bind(this);
    } else {
      this._boundHandleClick = this._handleClickSingle.bind(this);
    }
    this._boundFocusIn = this._focusIn.bind(this);
    this._boundFocusOut = this._focusOut.bind(this);
    if ( ! this._options ) this._options = [];
    this._body = new Element(document.body);
    this._create(element);
    // set initial selections, make sure this._config.value is valid or null before returning
    if ( this._config.multiple ) {
      let values = this._config.value; this._config.value = []; this._setValues(values, true);
    } else {
      let value = this._config.value; this._config.value = null; this._setValue(value, true);
      if ( this._config.value === null ) {
        let i = 0;
        for ( ; i < this._config.options.length && this._config.options[i].disabled ; i++ );
        if ( i < this._config.options.length ) this._setValue(this._config.options[i].value, true);
      }
    }
  }

  // Public API
  value(v) { if (v !== undefined) { this._setValue(v); } return this._config.value; }
  reset() { this._setValue(null); }
  open() { this._open(); }
  close() { this._close(); }
  next() { this._next(); }
  prev() { this._prev(); }

  // Private methods
  _create(_element) {
    const element = typeof _element === "string" ? document.querySelector(_element) : _element;
    if ( element.tagName != "SPAN"  ) throw "expected a span in SelectPure constructor";
    this._parent = new Element(element);
    this._select = new Element("div", { class: this._config.classNames.select });
    this._label = new Element("span", { class: this._config.classNames.label });
    this._optionsWrapper = new Element("div", { class: this._config.classNames.dropdown });
    this._options = this._generateOptions();
    this._select.addEventListener("click", this._boundHandleClick);
    this._select.append(this._label.get());
    this._select.append(this._optionsWrapper.get());
    this._parent.append(this._select.get());
    if ( this._config.multiple ) this._select.addClass(this._config.classNames.multiselect);
    this._placeholder = new Element("span", { class: this._config.classNames.placeholder, textContent: this._config.placeholder });
    this._select.append(this._placeholder.get());
    element.addEventListener('focusin', this._boundFocusIn);
    element.addEventListener('focusout', this._boundFocusOut);
  }

  _generateOptions() {
    if ( this._config.autocomplete ) {
      this._autocomplete = new Element("input", { class: this._config.classNames.autocompleteInput, type: "text" });
      this._autocomplete.addEventListener("input", this._boundNarrowOptions);
      this._autocomplete.spellcheck = false; // this doesn't work for some reason...
      this._optionsWrapper.append(this._autocomplete.get());
    }
    return this._config.options.map(_option => {
      const option = new Element("div", {
        class: `${this._config.classNames.option}${_option.disabled ? " " + this._config.classNames.optionDisabled : ""}`,
        value: _option.value,
        textContent: _option.label,
        disabled: _option.disabled,
      });
      if ( _option.disabled ) this._config.disabledOptions.push(String(_option.value));
      this._optionsWrapper.append(option.get());
      return option;
    });
  }

  _focusIn() { this._select.addClass(this._config.classNames.focus); }
  _focusOut() { this._select.removeClass(this._config.classNames.focus); }

  _open() {
    if ( this._state.opened ) return;
    this._select.addClass(this._config.classNames.selectOpen);
    this._body.addEventListener("click", this._boundHandleClick);
    this._select.removeEventListener("click", this._boundHandleClick);
    // manually implement overflow-y:auto (css won't work in firefox)
    this._optionsWrapper._node.style.overflowY =
      this._optionsWrapper._node.scrollHeight <= this._optionsWrapper._node.clientHeight+2 ? 'hidden' : 'scroll';
    this._state.opened = true;
    if ( this._autocomplete ) this._autocomplete.focus();
  }

  _close() {
      if ( ! this._state.opened ) return;
      this._select.removeClass(this._config.classNames.selectOpen);
      this._body.removeEventListener("click", this._boundHandleClick);
      this._select.addEventListener("click", this._boundHandleClick);
      this._state.opened = false;
  }

  _next() {
    if ( this._config.multiple ) return false;
    let i = this._config.options.findIndex(x => x.value === this._config.value);
    if ( i < 0 ) i = 0;
    for ( i++ ; i < this._config.options.length && this._config.options[i].disabled ; i++ );
    if ( i >= this._config.options.length ) return false;
    this._setValue(this._config.options[i].value);
    return true;
  }

  _prev() {
    if ( this._config.multiple ) return false;
    let i = this._config.options.findIndex(x => x.value === this._config.value);
    if ( i < 1 ) return false;
    for ( i-- ; i && this._config.options[i].disabled ; i-- );
    if ( i < 0 ) return false;
    this._setValue(this._config.options[i].value);
    return true;
  }

  _updatePlaceholder(hidden) {
    if ( hidden ) {
      this._placeholder.addClass(this._config.classNames.placeholderHidden);
      this._placeholder._setTextContent("");
    } else {
      this._placeholder.removeClass(this._config.classNames.placeholderHidden);
      this._placeholder._setTextContent(this._config.placeholder);
    }
  }

  _handleClickSingle(event) {
    event.stopPropagation();
    if ( event.target.className === this._config.icon ) return;
    if ( event.target.className === this._config.classNames.autocompleteInput ) return;
    if ( ! this._state.opened ) { this._open(); return; }
    const option = this._options.find(_option => _option.get() === event.target);
    if ( option && ! option.get().classList.contains(this._config.classNames.optionSelected) )
        this._setValue(option.get().getAttribute("data-value"));
    this._close();
  }

  _setValue(value, init=false) {
    if ( this._config.multiple ) return this._setValues(value);
    if ( ! value) value = '';
    if ( this._config.disabledOptions.indexOf(value) > -1 ) return false;
    const option = this._config.options.find(_option => _option.value === value);
    if ( ! option ) return false;
    this._options.forEach(_option => { _option.removeClass(this._config.classNames.optionSelected); });
    if ( value ) {
      const optionNode = this._options.find (_option => _option.get().getAttribute("data-value") === value);
      optionNode.addClass(this._config.classNames.optionSelected);
    }
    this._updatePlaceholder(value);
    this._selectedOption = option;
    this._label.setText(option.label);
    if ( this._config.value != value ) {
      this._config.value = value;
      if ( !init && this._config.onChange ) this._config.onChange(value);
    }
    return true;
  }

  _handleClickMultiple(event) {
    event.stopPropagation();
    if ( event.target.className === this._config.icon ) return;
    if ( event.target.className === this._config.classNames.autocompleteInput ) return;
    if ( ! this._state.opened ) { this._open(); return; }
    const option = this._options.find(_option => _option.get() === event.target);
    if ( ! option ) { this._close(); return; }
    if ( option.get().classList.contains(this._config.classNames.optionSelected) ) {
      this._unselectOption(event);
    } else {
      const value = option.get().getAttribute("data-value");
      if ( this._config.disabledOptions.indexOf(value) > -1 ) return;
      const values = value ? [...this._config.value || [], value] : [];
      if ( values.length > this._config.limit ) {
        if ( this._config.onLimit ) this._config.onLimit(this._config.limit);
      } else {
        this._setValues(values);
      }
      if ( values.length >= this._config.limit ) this._close();
    }
  }

  _setValues(values, init=false) {
    if ( ! this._config.multiple ) return this._setValue(values);
    if ( ! values ) values = [];
    values.filter(val => val && this._config.disabledOptions.indexOf(val) == -1 && this._config.options.indexOf(val) >= 0);
    if ( this._config.value ) this._options.forEach(_option => { _option.removeClass(this._config.classNames.optionSelected); });
    this._updatePlaceholder(values.length);
    const options = values.map(_value => {
      const option = this._config.options.find(_option => _option.value === _value);
      const optionNode = this._options.find(_option => _option.get().getAttribute("data-value") === option.value);
      optionNode.addClass(this._config.classNames.optionSelected);
      return option;
    });
    this._label.setText("");
    this._icons = options.map(_option => {
      const tag = new Element("span", { class: this._config.classNames.tag, textContent: this._config.shortTags ? _option.value : _option.label });
      const itype = this._config.inlineIcon ? this._config.inlineIcon.cloneNode(true) : "i";
      const icon = new Element(itype, { class: this._config.icon, value: _option.value });
      icon.addEventListener("click", this._boundUnselectOption);
      tag.append(icon.get());
      this._label.append(tag.get());
      return icon.get();
    });
    if ( this._config.value != values ) {
      this._config.value = values;
      if ( ! init && this._config.onChange ) this._config.onChange(values);
    }
    return true;
  }

  _unselectOption(event) {
    event.stopPropagation();
    const newValue = [...this._config.value];
    const index = newValue.indexOf(event.target.getAttribute("data-value"));
    if ( index !== -1 ) newValue.splice(index, 1);
    this._setValues(newValue);
  }

  _narrowOptions(event) {
    this._options.forEach(_option => {
      if ( ! _option.get().textContent.toLowerCase().includes(event.target.value.toLowerCase()) ) {
        _option.addClass(this._config.classNames.optionHidden);
        return;
      }
      _option.removeClass(this._config.classNames.optionHidden);
    });
  }
}
