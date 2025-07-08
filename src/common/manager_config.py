import configparser
import json
import os

class ConfigManager:
    def __init__(self, cache_dir='app_cache'):
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # Specific tool/feature settings
        self.ip_config_path = os.path.join(self.cache_dir, 'ipconfig.ini')
        self.parse_ini_path = os.path.join(self.cache_dir, 'parse.ini')
        self.svn_ini_path = os.path.join(self.cache_dir, 'svn_config.ini')
        self.raw_settings_path = os.path.join(self.cache_dir, 'raw_settings.json')
        self.pic_ini_path = os.path.join(self.cache_dir, 'pic.ini')

        self.config = configparser.ConfigParser()
        self.ip_config = configparser.ConfigParser()
        self.parse_config = configparser.ConfigParser()
        self.svn_config = configparser.ConfigParser()
        self.pic_config = configparser.ConfigParser()

        self._init_default_configs()

    def _init_default_configs(self):
        """Initialize or create config files with default values."""
        # --- IP config.ini in root ---
        if not os.path.exists(self.ip_config_path):
            self.ip_config['API'] = {'host': '127.0.0.1', 'port': '8000'}
            with open(self.ip_config_path, 'w', encoding='utf-8') as f: self.ip_config.write(f)
        else:
            self.ip_config.read(self.ip_config_path, encoding='utf-8')

        # --- Parse.ini ---
        if not os.path.exists(self.parse_ini_path):
            self.parse_config['settings'] = {'parse_processes': '4', 'dump_processes': '2', 'batch_size': '50'}
            with open(self.parse_ini_path, 'w', encoding='utf-8') as f: self.parse_config.write(f)
        else:
            self.parse_config.read(self.parse_ini_path, encoding='utf-8')

        # --- Svn.ini ---
        if not os.path.exists(self.svn_ini_path):
            self.svn_config['svn'] = {'url': '', 'username': '', 'password': ''}
            with open(self.svn_ini_path, 'w', encoding='utf-8') as f: self.svn_config.write(f)
        else:
            self.svn_config.read(self.svn_ini_path, encoding='utf-8')

        # --- Pic.ini ---
        if not os.path.exists(self.pic_ini_path):
            self.pic_config['settings'] = {'rgb_lab_enabled': 'false', 'histogram_enabled': 'false', 'clear_cache': 'false'}
            with open(self.pic_ini_path, 'w', encoding='utf-8') as f: self.pic_config.write(f)
        else:
            self.pic_config.read(self.pic_ini_path, encoding='utf-8')

        # --- JSON configs ---
        self._init_json_config(self.raw_settings_path, {
            "width": "3264",
            "height": "2448",
            "bit_depth": "10",
            "bayer_pattern": "RGGB"
        })

    def _init_json_config(self, path, default_data):
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, indent=4)

    def get_config(self, config_name):
        """Get a config parser object."""
        config_obj, _ = self._get_config_object_and_path(config_name)
        return config_obj

    def save_config(self, config_name):
        """Save the config file."""
        config_obj, path = self._get_config_object_and_path(config_name)
        if config_obj and path:
            with open(path, 'w', encoding='utf-8') as f:
                config_obj.write(f)

    def get_setting(self, section, key, file_type='ini', config_name=None, default=None):
        """Get a setting value. `config_name` specifies which config to use."""
        try:
            if file_type == 'ini':
                config_obj, _ = self._get_config_object_and_path(config_name)
                if config_obj is None: return default

                if config_obj.has_option(section, key):
                    val = config_obj.get(section, key)
                    if isinstance(val, str):
                        if val.lower() in ['true', 'yes', 'on']: return True
                        if val.lower() in ['false', 'no', 'off']: return False
                    return val
                return default
            
            elif file_type == 'json':
                _, path = self._get_config_object_and_path(config_name)
                if path is None: return default
                with open(path, 'r', encoding='utf-8') as f: data = json.load(f)

                if config_name == 'raw':
                    return data.get(key, default)

                val = data.get(section, {}).get(key)
                return val if val is not None else default
                
        except (configparser.Error, FileNotFoundError, json.JSONDecodeError, AttributeError):
            return default
        return default

    def set_setting(self, section, key, value, file_type='ini', config_name=None):
        """Set a setting value. `config_name` specifies which config to use."""
        try:
            if file_type == 'ini':
                config_obj, path = self._get_config_object_and_path(config_name)
                if config_obj is None: return

                if not config_obj.has_section(section):
                    config_obj.add_section(section)
                
                value_str = str('true' if value is True else 'false' if value is False else value)
                config_obj.set(section, key, value_str)
                with open(path, 'w', encoding='utf-8') as f: config_obj.write(f)
            
            elif file_type == 'json':
                _, path = self._get_config_object_and_path(config_name)
                if path is None: return
                try:
                    with open(path, 'r', encoding='utf-8') as f: data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    data = {}
                
                if config_name == 'raw':
                    data[key] = value
                else:
                    data.setdefault(section, {})[key] = value

                with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)

        except (configparser.Error, FileNotFoundError, AttributeError):
            pass # Or log an error

    def _get_config_object_and_path(self, config_name):
        """Helper to get the right config parser and path based on a name."""
        if config_name == 'ip':
            return self.ip_config, self.ip_config_path
        if config_name == 'parse':
            return self.parse_config, self.parse_ini_path
        if config_name == 'svn':
            return self.svn_config, self.svn_ini_path
        if config_name == 'pic':
            return self.pic_config, self.pic_ini_path
        if config_name == 'raw':
            return None, self.raw_settings_path
        return None, None 