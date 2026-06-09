PACKAGE_NAME ?= AutoAppearance
BUILD_DIR ?= dist
PACKAGE_PATH := $(BUILD_DIR)/$(PACKAGE_NAME).sublime-package

PACKAGE_FILES := \
	auto_appearance.py \
	AutoAppearance.sublime-settings \
	Default.sublime-commands \
	Main.sublime-menu \
	messages.json \
	messages/install.txt \
	README.md \
	LICENSE

.PHONY: all build install clean

all: build

build: $(PACKAGE_PATH)

$(PACKAGE_PATH): $(PACKAGE_FILES)
	@mkdir -p "$(BUILD_DIR)"
	@tmp_dir="$$(mktemp -d "$(BUILD_DIR)/.$(PACKAGE_NAME).build.XXXXXX")"; \
	tmp_package="$$tmp_dir/$(PACKAGE_NAME).sublime-package"; \
	trap 'rm -rf "$$tmp_dir"' EXIT; \
	if command -v zip >/dev/null 2>&1; then \
		zip -q -X "$$tmp_package" $(PACKAGE_FILES); \
	elif command -v python3 >/dev/null 2>&1; then \
		python3 -m zipfile -c "$$tmp_package" $(PACKAGE_FILES); \
	else \
		echo "Could not find zip or python3 to create the package." >&2; \
		exit 1; \
	fi; \
	mv -f "$$tmp_package" "$(PACKAGE_PATH)"
	@echo "Built $(abspath $(PACKAGE_PATH))"

install: build
	@installed_packages_dir="$(SUBLIME_INSTALLED_PACKAGES_DIR)"; \
	if [ -z "$$installed_packages_dir" ]; then \
		for candidate in \
			"$$HOME/.config/sublime-text/Installed Packages" \
			"$$HOME/.config/sublime-text-4/Installed Packages" \
			"$$HOME/.config/sublime-text-3/Installed Packages"; do \
			if [ -d "$$candidate" ]; then \
				installed_packages_dir="$$candidate"; \
				break; \
			fi; \
		done; \
	fi; \
	if [ -z "$$installed_packages_dir" ]; then \
		installed_packages_dir="$$HOME/.config/sublime-text/Installed Packages"; \
	fi; \
	mkdir -p "$$installed_packages_dir"; \
	cp "$(PACKAGE_PATH)" "$$installed_packages_dir/$(PACKAGE_NAME).sublime-package"; \
	echo "Installed $(PACKAGE_NAME).sublime-package"; \
	echo "Destination: $$installed_packages_dir"; \
	echo "Restart Sublime Text if the package does not load immediately."

clean:
	@rm -rf "$(BUILD_DIR)"
