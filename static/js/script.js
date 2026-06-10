(function () {
  const storageKey = "synclyTheme";
  const body = document.body;
  const themeToggle = document.getElementById("themeToggle");
  const mainHeader = document.querySelector(".main-header");
  const mobileSearchToggle = document.getElementById("mobileSearchToggle");
  const mobileSearchInput = document.querySelector(".header-center input[name='query']");
  const userMenu = document.getElementById("userMenu");
  const userMenuBtn = document.getElementById("userMenuBtn");

  if (localStorage.getItem(storageKey) === "light") {
    body.classList.add("light");
  }

  const syncThemeScene = initSynclyBackground();

  themeToggle?.addEventListener("click", () => {
    const isLight = body.classList.toggle("light");
    localStorage.setItem(storageKey, isLight ? "light" : "yellow-black");
    syncThemeScene?.setTheme(isLight ? "light" : "dark");

    if (window.gsap) {
      gsap.fromTo("body", { opacity: 0.92 }, { opacity: 1, duration: 0.22, ease: "power2.out" });
    }
  });

  userMenuBtn?.addEventListener("click", () => {
    userMenu?.classList.toggle("open");
    userMenuBtn.setAttribute("aria-expanded", userMenu?.classList.contains("open") ? "true" : "false");
  });

  mobileSearchToggle?.addEventListener("click", () => {
    const isOpen = mainHeader?.classList.toggle("mobile-search-open");
    mobileSearchToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    mobileSearchToggle.setAttribute("aria-label", isOpen ? "Close search" : "Open search");
    if (isOpen) {
      setTimeout(() => mobileSearchInput?.focus(), 80);
    }
  });

  document.addEventListener("click", (event) => {
    if (userMenu && !userMenu.contains(event.target)) {
      userMenu.classList.remove("open");
      userMenuBtn?.setAttribute("aria-expanded", "false");
    }
    if (
      mainHeader?.classList.contains("mobile-search-open") &&
      !event.target.closest(".header-center") &&
      !event.target.closest("#mobileSearchToggle")
    ) {
      mainHeader.classList.remove("mobile-search-open");
      mobileSearchToggle?.setAttribute("aria-expanded", "false");
      mobileSearchToggle?.setAttribute("aria-label", "Open search");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mainHeader?.classList.contains("mobile-search-open")) {
      mainHeader.classList.remove("mobile-search-open");
      mobileSearchToggle?.setAttribute("aria-expanded", "false");
      mobileSearchToggle?.setAttribute("aria-label", "Open search");
      mobileSearchToggle?.focus();
    }
  });

  if (window.gsap) {
    body.classList.add("gsap-ready");

    gsap.to(".animate-in, .form-card, .auth-card, .delete-card", {
      opacity: 1,
      y: 0,
      duration: 0.48,
      ease: "power3.out",
      stagger: 0.06,
      clearProps: "transform"
    });

    gsap.fromTo(".page-hero, .page-header", { opacity: 0, y: 18 }, {
      opacity: 1,
      y: 0,
      duration: 0.5,
      ease: "power3.out"
    });

    gsap.to(".room-card, .activity-item, .topic-tag", {
      opacity: 1,
      y: 0,
      duration: 0.42,
      ease: "power2.out",
      stagger: 0.045,
      clearProps: "transform"
    });

    document.querySelectorAll(".room-card, .activity-item, .topic-tag, .primary-action, .secondary-action").forEach((el) => {
      el.addEventListener("mouseenter", () => gsap.to(el, { y: -2, duration: 0.18, ease: "power2.out" }));
      el.addEventListener("mouseleave", () => gsap.to(el, { y: 0, duration: 0.18, ease: "power2.out" }));
    });
  } else {
    body.classList.remove("gsap-ready");
  }

  function initSynclyBackground() {
    const canvas = document.getElementById("syncly-bg");
    if (!canvas || !window.THREE) return null;
    const prefersReducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    const saveData = navigator.connection?.saveData;
    const smallScreen = window.innerWidth < 900;
    if (prefersReducedMotion || saveData || smallScreen) {
      canvas.setAttribute("hidden", "");
      return null;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0, 8);

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "low-power" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.35));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const group = new THREE.Group();
    scene.add(group);
    const accents = new THREE.Group();
    scene.add(accents);

    const particleCount = 90;
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i += 1) {
      const i3 = i * 3;
      positions[i3] = (Math.random() - 0.5) * 19;
      positions[i3 + 1] = (Math.random() - 0.5) * 11;
      positions[i3 + 2] = -1 - Math.random() * 7;
    }

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const particleMaterial = new THREE.PointsMaterial({
      color: 0xffd21f,
      size: 0.052,
      transparent: true,
      opacity: 0.42,
      depthWrite: false
    });
    const particles = new THREE.Points(particleGeometry, particleMaterial);
    group.add(particles);

    const nodeCount = 16;
    const nodePositions = [];
    const nodeGeometry = new THREE.BufferGeometry();
    const nodePositionBuffer = new Float32Array(nodeCount * 3);
    for (let i = 0; i < nodeCount; i += 1) {
      const point = new THREE.Vector3(
        (Math.random() - 0.5) * 17,
        (Math.random() - 0.5) * 9.5,
        -2.5 - Math.random() * 4
      );
      nodePositions.push(point);
      nodePositionBuffer[i * 3] = point.x;
      nodePositionBuffer[i * 3 + 1] = point.y;
      nodePositionBuffer[i * 3 + 2] = point.z;
    }
    nodeGeometry.setAttribute("position", new THREE.BufferAttribute(nodePositionBuffer, 3));
    const nodeMaterial = new THREE.PointsMaterial({
      color: 0xffd21f,
      size: 0.095,
      transparent: true,
      opacity: 0.38,
      depthWrite: false
    });
    const nodes = new THREE.Points(nodeGeometry, nodeMaterial);
    accents.add(nodes);

    const connectionGeometry = new THREE.BufferGeometry();
    const connectionPositions = [];
    for (let i = 0; i < nodePositions.length; i += 1) {
      for (let j = i + 1; j < nodePositions.length; j += 1) {
        if (nodePositions[i].distanceTo(nodePositions[j]) < 3.15 && connectionPositions.length < 180) {
          connectionPositions.push(
            nodePositions[i].x, nodePositions[i].y, nodePositions[i].z,
            nodePositions[j].x, nodePositions[j].y, nodePositions[j].z
          );
        }
      }
    }
    connectionGeometry.setAttribute("position", new THREE.Float32BufferAttribute(connectionPositions, 3));
    const connectionMaterial = new THREE.LineBasicMaterial({
      color: 0xffd21f,
      transparent: true,
      opacity: 0.11,
      depthWrite: false
    });
    const connections = new THREE.LineSegments(connectionGeometry, connectionMaterial);
    accents.add(connections);

    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0xffd21f,
      transparent: true,
      opacity: 0.12,
      wireframe: true,
      depthWrite: false
    });

    const rings = [];
    for (let i = 0; i < 3; i += 1) {
      const geometry = new THREE.TorusGeometry(1.15 + i * 0.45, 0.012, 10, 96);
      const ring = new THREE.Mesh(geometry, ringMaterial.clone());
      ring.position.set((i - 1.5) * 3.2, i % 2 ? 2.4 : -2.3, -2 - i * 0.6);
      ring.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
      rings.push(ring);
      group.add(ring);
    }

    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0xffd21f,
      transparent: true,
      opacity: 0.1
    });

    for (let i = 0; i < 5; i += 1) {
      const path = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-7 + Math.random() * 2, -4 + Math.random() * 8, -2 - Math.random() * 2),
        new THREE.Vector3(7 - Math.random() * 2, -4 + Math.random() * 8, -2 - Math.random() * 2)
      ]);
      group.add(new THREE.Line(path, lineMaterial.clone()));
    }

    const shapeMaterials = [];
    const shapes = [];
    const shapeGeometry = new THREE.IcosahedronGeometry(0.55, 1);
    const shapePositions = [
      [-6.4, 2.9, -4.2],
      [6.7, 3.1, -4.7],
      [-7.1, -2.6, -4.8],
      [7.4, -2.4, -4.1],
      [-3.9, 4.2, -5.5],
      [3.7, -4.1, -5.2]
    ];

    shapePositions.forEach((position, index) => {
      const material = new THREE.MeshBasicMaterial({
        color: index % 2 ? 0x111111 : 0xffd21f,
        transparent: true,
        opacity: 0.09,
        wireframe: true,
        depthWrite: false
      });
      const shape = new THREE.Mesh(shapeGeometry, material);
      shape.position.set(position[0], position[1], position[2]);
      shape.rotation.set(index * 0.8, index * 0.45, index * 0.25);
      shape.scale.setScalar(0.72 + index * 0.08);
      shapeMaterials.push(material);
      shapes.push(shape);
      accents.add(shape);
    });

    const haloGeometry = new THREE.RingGeometry(1.8, 1.84, 96);
    const haloMaterial = new THREE.MeshBasicMaterial({
      color: 0xffd21f,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    const haloLeft = new THREE.Mesh(haloGeometry, haloMaterial.clone());
    haloLeft.position.set(-6.8, 0.2, -5.8);
    haloLeft.rotation.set(0.75, 0.15, 0.4);
    const haloRight = new THREE.Mesh(haloGeometry, haloMaterial.clone());
    haloRight.position.set(6.9, -0.15, -5.8);
    haloRight.rotation.set(-0.55, -0.3, -0.25);
    accents.add(haloLeft, haloRight);
    const halos = [haloLeft, haloRight];

    function applyTheme(mode) {
      const light = mode === "light";
      particleMaterial.color.set(light ? 0xc89600 : 0xffd21f);
      particleMaterial.opacity = light ? 0.34 : 0.42;
      nodeMaterial.color.set(light ? 0x111111 : 0xffd21f);
      nodeMaterial.opacity = light ? 0.22 : 0.38;
      connectionMaterial.color.set(light ? 0xc89600 : 0xffd21f);
      connectionMaterial.opacity = light ? 0.13 : 0.11;
      rings.forEach((ring, index) => {
        ring.material.color.set(light ? 0xc89600 : 0xffd21f);
        ring.material.opacity = light ? 0.08 + index * 0.015 : 0.1 + index * 0.018;
      });
      shapeMaterials.forEach((material, index) => {
        material.color.set(light ? (index % 2 ? 0x111111 : 0xd6a900) : (index % 2 ? 0xffe982 : 0xffd21f));
        material.opacity = light ? 0.075 : 0.09;
      });
      halos.forEach((halo, index) => {
        halo.material.color.set(light ? (index ? 0x111111 : 0xd6a900) : 0xffd21f);
        halo.material.opacity = light ? 0.055 : 0.08;
      });
      group.children.forEach((child) => {
        if (child.type === "Line") {
          child.material.color.set(light ? 0xc89600 : 0xffd21f);
          child.material.opacity = light ? 0.075 : 0.1;
        }
      });
    }

    applyTheme(body.classList.contains("light") ? "light" : "dark");

    let rafId;
    function animate() {
      rafId = requestAnimationFrame(animate);
      const time = performance.now() * 0.00022;
      particles.rotation.y = time;
      particles.rotation.x = Math.sin(time * 0.7) * 0.08;
      accents.rotation.y = Math.sin(time * 0.8) * 0.08;
      accents.rotation.x = Math.cos(time * 0.55) * 0.035;
      nodes.rotation.z = time * 0.7;
      connections.rotation.z = time * 0.7;
      rings.forEach((ring, index) => {
        ring.rotation.x += 0.0014 + index * 0.00025;
        ring.rotation.y += 0.0018 + index * 0.0002;
      });
      shapes.forEach((shape, index) => {
        shape.rotation.x += 0.0012 + index * 0.00018;
        shape.rotation.y += 0.0016 + index * 0.00016;
        shape.position.y += Math.sin(performance.now() * 0.00045 + index) * 0.0009;
      });
      halos.forEach((halo, index) => {
        halo.rotation.z += (index ? -1 : 1) * 0.0009;
      });
      renderer.render(scene, camera);
    }

    function resize() {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }

    window.addEventListener("resize", resize);
    animate();

    return {
      setTheme: applyTheme,
      destroy() {
        cancelAnimationFrame(rafId);
        window.removeEventListener("resize", resize);
        renderer.dispose();
        particleGeometry.dispose();
        particleMaterial.dispose();
        rings.forEach((ring) => {
          ring.geometry.dispose();
          ring.material.dispose();
        });
        nodeGeometry.dispose();
        nodeMaterial.dispose();
        connectionGeometry.dispose();
        connectionMaterial.dispose();
        shapeGeometry.dispose();
        shapeMaterials.forEach((material) => material.dispose());
        halos.forEach((halo) => {
          halo.geometry.dispose();
          halo.material.dispose();
        });
      }
    };
  }
})();
