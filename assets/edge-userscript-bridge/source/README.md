# Tampermonkey Editors

本分支在官方 Editors 基础上增加了可选的 Native Messaging 自动桥接。扩展安装并注册一次本地 host 后，后台会自动连接 Tampermonkey，不再要求日常输入连接码；原有 WebSocket/连接码流程仍保留为兼容后备。实现和安装说明见 [`bridge/README.md`](bridge/README.md)。

## Building

```bash
./build_sys/mkrelease.sh -v 999
```

The extension packages then can be found at the `./release/` folder.

## Testing with Tampermonkey

```bash
mkdir -p other/tampermonkey
cd other/tampermonkey
wget https://www.tampermonkey.net/crx/tampermonkey_stable.crx
unzip tampermonkey_stable.crx
sed -i 's/"hohmicmmlneppdcbkhepamlgfdokipcd"/"kjmbknaomholdmpocgplbkgmjdnidinh"/' background.js
```

Start Chrome, go to `chrome://extensions/`, enable Developer mode, and click on `Load unpacked` and select the `other/tampermonkey` folder.
Search for "Tampermonkey" in the extensions list and copy the ID (e.g. `iomhjoeebbnlcpalefgjmleebfffgbmm`).
Now search for `Tampermonkey Editors` and click at `Inspect views: service worker` to open the console and paste the following code after you've changed the ID (`iomh...`) to the one you've copied before:

```javascript
chrome.storage.local.set({ 'config': { externalExtensionIds: [ 'iomhjoeebbnlcpalefgjmleebfffgbmm' ] } })
.then(() => {
    chrome.runtime.reload()
});
```

Now install a userscript in Tampermonkey and click at the `Tampermonkey Editors` icon in the toolbar to see the editor.
