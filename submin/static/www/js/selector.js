/* Constructor. Options is a dictionary.
 * Expected options:
 * - selectorId: The id of the ul to add f.i. every group and the
 *   	dropdown with all the remaining groups to.
 * - urlPrefix: The name of the current item is added to this prefix to link
 *   	to f.i. a group
 * - initCallback: callback-function which returns two lists in a dictionary:
 *   	added and addable. The first being the list with the items which are
 *   	already part of the Selector, and addable items which can be added.
 *   	This method is also called when re-initializing after a change.
 * - addCallback: callback-function, expecting the name of the item to be
 *   	added. This usually does an Ajax-request to add f.i. a user to a group.
 * - removeCallback: Analogous to addCallback, only for removing. Also expects
 *   	the name of the item to be removed.
 * - canLink: is a user allowed to see a link to the other object? This is a
 *   	function, expecting the name of the current object.
 * - canEdit: is a user allowed to add and remove, or only view? This is also
 *   	a function, but has no arguments.
 * - type: "permissions" if permission selector, users/groups otherwise
 *
 * WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
 *
 * The init/add/remove calbacks must call the reInit() of the Selector
 * object, because these callbacks can be asynchronous and the Selector
 * object does not know when to refresh.
 * 
 * WARNING WARNING WARNING WARNING WARNING WARNING WARNING WARNING
 */
function Selector(options) {
	this.options = options;
	this.list = document.getElementById(this.options.selectorId);
	this.reInit();
}

/* Creates the add/remove button for each item */
Selector.prototype.makeButton = function(className) {
	var minus = $c("div", {"className": className});
	addClassName(minus, "c_icon");
	addClassName(minus, "minus");
	return minus;
}

/* Reinitializes the list after a change. */
Selector.prototype.reInit = function() {
	// Make the list empty before calling init().
	for (var item_idx=this.list.childNodes.length; item_idx--;)
		this.list.removeChild(this.list.childNodes[item_idx]);
	this.init();
}

function permissionSort(a, b)
{
	var type_diff = humanCmp(a.type, b.type)
	if (type_diff != 0)
		return type_diff;

	return humanCmp(a.name, b.name);
}

function stringSort(a, b)
{
	return humanCmp(a, b);
}

Selector.prototype.init = function() {
	var callbackValue;
	if (this.options.type == "permissions") {
		callbackValue = this.options.initCallback(this.options.path);
	} else {
		callbackValue = this.options.initCallback();
	}
	// The dropdown

	// Show dropdown only if users can edit.
	if (this.options.canEdit()) {
		var addable = callbackValue["addable"];
		if (this.options.type == "permissions") {
			addable.sort(permissionSort);
		} else {
			addable.sort(stringSort);
		}
		this.setupSelect(addable);
	}

	// The li-items
	var added = callbackValue["added"];
	if (this.options.type == "permissions") {
		added.sort(permissionSort);
	} else {
		added.sort(stringSort);
	}
	for (var added_idx=0; added_idx < added.length; ++added_idx)
		this.setupAddedItem(added[added_idx]);
}

Selector.prototype.permissionsSelect = function(name, type, permissions) {
	var select = $c("select");
	if (this.options.vcs_type == "git") {
		if (this.options.path == "/") {
			var values = ['r', 'rw'];
		} else {
			var values = ['w'];
		}
		var inner = values;
	} else {
		var values = ['', 'r', 'rw'];
		var inner = ['-', 'r', 'rw'];
	}
	for (var idx = 0; idx < values.length; ++idx) {
		select.appendChild($c("option", {'value': values[idx], 'innerHTML': inner[idx]}));
		if (values[idx] == permissions)
			select.selectedIndex = idx;
	}
	var _this = this;
	select.onchange = function() {
		var permissions = values[parseInt(select.selectedIndex)];
		_this.options.changeCallback(name, type, permissions, _this.options.path);
		return false;
	};
	return select;
}

Selector.prototype.setupAddedItem = function(added) {
		var item = $c("li");
		if (this.options.type == "permissions") {
			item.name = added['name'];
			var permissions = added['permissions'];
			if (permissions == "")
				permissions = "none";
			var icons = {"user": "UserIconScaled.png",
				"group": "GroupIconScaled.png"}
			var img = $c("img",
					{"src": base_url + "img/" + icons[added["type"]]});
			var displayname = added["name"];
			var span = $c("span");
			span.appendChild(img);
			span.appendChild(document.createTextNode(displayname));
			item.appendChild(span);
		} else {
			item.name = added;
			if (!this.options.canLink(added)) {
				item.appendChild(document.createTextNode(added));
			} else {
				var link = $c("a", {"href": this.options.urlPrefix + added});
				link.appendChild(document.createTextNode(added));
				item.appendChild(link);
			}
		}

		if (this.options.canEdit()) {
			var remover = this.makeButton("remover");
			item.appendChild(remover);

			var _this = this; // this is out of scope in onclick below!
			var _name = item.name;
			if (this.options.type == "permissions") {
				var _type = added["type"];
				var _perm = added["permissions"];

				item.appendChild(this.permissionsSelect(_name, _type, _perm));
				remover.onclick = function() {
					_this.removerOnClick(_name, _type);
				};
			} else {
				remover.onclick = function() { _this.removerOnClick(_name); };
			}

		}

		this.list.appendChild(item);
}

Selector.prototype.removerOnClick = function(name, type) {
	this.options.removeCallback(name, type, this.options.path);
	return false;
};

Selector.prototype.setupSelect = function(addable) {
	this.select = $c("select", {"className": "adder"});

	var item = $c("li");
	var span = $c("span", {"innerHTML": "Add: "});
	item.appendChild(span);
	item.appendChild(this.select);
	var _this = this; // this is out of scope in onclick below!

	this.select.onchange = function() { _this.selectOnChange(); };

	if (this.options.type == "permissions") {
		this.addOption({"type": "", "name": "---"});
	} else {
		this.addOption("---");
	}

	if (this.options.type == "permissions") {
		this.groupOptions = $c("optgroup");
		this.groupOptions.setAttribute("label", "Groups");
		this.userOptions = $c("optgroup");
		this.userOptions.setAttribute("label", "Users");
		this.select.appendChild(this.groupOptions);
		this.select.appendChild(this.userOptions);
	}


	for (var addable_idx = 0; addable_idx < addable.length; ++addable_idx)
		this.addOption(addable[addable_idx]);

	this.list.appendChild(item);

	if (!addable.length)
		this.select.disabled = true;
}

Selector.prototype.selectOnChange = function() {
	var select = this.select;
	var groupname = select.options[select.selectedIndex].getAttribute("value");
	var displayname = select.options[select.selectedIndex].innerHTML;

	if (groupname == "---") {
		Log('Please select an item first', 'error')
		return false;
	}

	if (this.options.type == "permissions") {
		this.options.addCallback(displayname, groupname, this.options.path);
	} else {
		this.options.addCallback(displayname);
	}

	return false;
}

Selector.prototype.addOption = function(_option) {
	var option = $c("option");
	if (this.options.type == "permissions") {
		option.value = _option.type;
		option.appendChild(document.createTextNode(_option.name));
		if (_option.type == "group") {
			this.groupOptions.appendChild(option);
		} else if (_option.type == "user") {
			this.userOptions.appendChild(option);
		} else {
			this.select.appendChild(option);
		}
	} else {
		option.value = _option;
		displayname = _option;

		option.appendChild(document.createTextNode(displayname));
		this.select.appendChild(option);
	}

}

// remove hooks to avoid memory leaks
// implemented depth-first iterative for performance reasons
Selector.prototype.destroy = function() {
	var current = this.list;
	for (;;) {
		if (current.onclick)
			current.onclick = null;
		if (current.onchange)
			current.onchange = null;

		if (current.firstChild) {
			current = current.firstChild;
			continue;
		}

		if (current.nextSibling) {
			current = current.nextSibling;
			continue;
		}

		do {
			current = current.parentNode;
			if (current == this.list)
				return; /* function will exit here, always */
		} while (!current.nextSibling);
		current = current.nextSibling;
	}
	/* not reached, see return above */
}

