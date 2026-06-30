/**
 * UDM v5.2β — underside flip + toroidal expansion view controller
 */
(function () {
  const API = `${window.EARTH_ORIGIN || window.location.origin}/api`;

  class UndersideViewController {
    constructor(camera, scene, opts = {}) {
      this.camera = camera;
      this.scene = scene;
      this.isUnderside = false;
      this.mode = 'top';
      this.transitionDuration = 800;
      this.onModeChange = opts.onModeChange || (() => {});
      this._startPos = null;
      this._animId = null;
    }

    setMode(mode) {
      if (mode === 'underside') this.flipToUnderside();
      else if (mode === 'toroidal') this.expandToToroidalView();
      else if (mode === 'top') this.flipToUpperSide();
      else {
        this.mode = mode;
        this.onModeChange(mode);
      }
    }

    flipToUnderside() {
      if (this.isUnderside && this.mode === 'underside') return;
      const startPos = this.camera.position.clone();
      const endPos = startPos.clone();
      endPos.z = -Math.abs(startPos.z) - 2.5;
      this._animate(startPos, endPos, this.camera.up.clone(), { x: 0, y: 0, z: -1 });
      this.isUnderside = true;
      this.mode = 'underside';
      this.onModeChange('underside');
    }

    flipToUpperSide() {
      const startPos = this.camera.position.clone();
      const endPos = startPos.clone();
      endPos.z = Math.abs(startPos.z) || 2.8;
      this._animate(startPos, endPos, this.camera.up.clone(), { x: 0, y: 0, z: 1 });
      this.isUnderside = false;
      this.mode = 'top';
      this.onModeChange('top');
    }

    expandToToroidalView() {
      const startPos = this.camera.position.clone();
      const endPos = { x: 4.5, y: 2.5, z: 5.5 };
      this._animate(startPos, endPos, this.camera.up.clone(), { x: 0, y: 0, z: 1 });
      this.mode = 'toroidal';
      this.onModeChange('toroidal');
    }

    _animate(startPos, endPos, startUp, endUp) {
      const startTime = performance.now();
      if (this._animId) cancelAnimationFrame(this._animId);
      const endUpV = new THREE.Vector3(endUp.x, endUp.y, endUp.z);
      const endPosV = endPos instanceof THREE.Vector3 ? endPos : new THREE.Vector3(endPos.x, endPos.y, endPos.z);
      const tick = (now) => {
        const t = Math.min((now - startTime) / this.transitionDuration, 1);
        const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        this.camera.position.lerpVectors(startPos, endPosV, ease);
        this.camera.up.lerpVectors(startUp, endUpV, ease).normalize();
        this.camera.lookAt(0, -0.4, 0);
        if (t < 1) this._animId = requestAnimationFrame(tick);
      };
      this._animId = requestAnimationFrame(tick);
    }
  }

  window.UDM_VIEW_MODES = { UndersideViewController, API };
})();