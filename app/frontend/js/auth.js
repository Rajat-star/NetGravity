/**
 * Netgravity — Authentication Controller (Sign In, Create Account, Reset Password)
 * ==============================================================================
 * Handles view switching, form validation, password visibility toggles,
 * auth state transitions, and integration with the main dashboard.
 */

// Track current view state
let currentAuthView = 'login'; // 'login' | 'signup' | 'forgot-password'

/**
 * Initialize Authentication Module
 */
export function initAuth() {
  bindAuthEvents();
  bindPasswordToggles();
  handleInitialUrl();
  setupHistoryListener();
}

/**
 * Handle initial URL on page load (support deep linking /login, /signup, /forgot-password)
 */
function handleInitialUrl() {
  const path = window.location.pathname.toLowerCase();
  const hash = window.location.hash.toLowerCase();

  if (path.includes('/login') || hash === '#login') {
    navigateToAuth('login', false);
  } else if (path.includes('/signup') || hash === '#signup' || hash === '#register') {
    navigateToAuth('signup', false);
  } else if (path.includes('/forgot-password') || hash === '#forgot-password' || hash === '#reset') {
    navigateToAuth('forgot-password', false);
  } else if (path.includes('/app') || hash === '#app') {
    if (typeof window.enterApp === 'function') {
      window.enterApp('home');
    }
  }
}

/**
 * Setup browser history popstate listener for back/forward navigation
 */
function setupHistoryListener() {
  window.addEventListener('popstate', (e) => {
    const state = e.state;
    if (state && state.view) {
      if (state.view === 'landing') {
        returnToLanding(false);
      } else if (state.view === 'app') {
        if (typeof window.enterApp === 'function') {
          window.enterApp('home', false);
        }
      } else {
        navigateToAuth(state.view, false);
      }
    } else {
      handleInitialUrl();
    }
  });
}

/**
 * Navigate to one of the authentication views ('login' | 'signup' | 'forgot-password')
 */
export function navigateToAuth(view = 'login', pushHistory = true) {
  currentAuthView = view;

  const landingPage = document.getElementById('landing-page');
  const authPage = document.getElementById('auth-page');
  const appShell = document.querySelector('.app-shell');

  // Hide Landing and App Shell
  if (landingPage) {
    landingPage.classList.add('hidden');
    landingPage.style.display = 'none';
  }
  if (appShell) {
    appShell.style.display = 'none';
  }

  // Show Auth Container
  if (authPage) {
    authPage.classList.remove('hidden');
    authPage.style.display = 'flex';
  }

  // Toggle specific form cards
  const loginCard = document.getElementById('auth-login-card');
  const signupCard = document.getElementById('auth-signup-card');
  const forgotCard = document.getElementById('auth-forgot-card');

  if (loginCard) loginCard.style.display = view === 'login' ? 'block' : 'none';
  if (signupCard) signupCard.style.display = view === 'signup' ? 'block' : 'none';
  if (forgotCard) forgotCard.style.display = view === 'forgot-password' ? 'block' : 'none';

  // Clear previous errors
  clearAuthErrors();

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'instant' });

  // Update browser URL
  if (pushHistory) {
    const targetUrl = view === 'login' ? '/login' : view === 'signup' ? '/signup' : '/forgot-password';
    try {
      window.history.pushState({ view }, '', targetUrl);
    } catch (e) {
      window.location.hash = `#${view}`;
    }
  }
}

/**
 * Return to the existing landing page
 */
export function returnToLanding(pushHistory = true) {
  const landingPage = document.getElementById('landing-page');
  const authPage = document.getElementById('auth-page');
  const appShell = document.querySelector('.app-shell');

  if (authPage) {
    authPage.classList.add('hidden');
    authPage.style.display = 'none';
  }
  if (appShell) {
    appShell.style.display = 'none';
  }
  if (landingPage) {
    landingPage.classList.remove('hidden');
    landingPage.style.display = 'flex';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (pushHistory) {
    try {
      window.history.pushState({ view: 'landing' }, '', '/');
    } catch (e) {
      window.location.hash = '';
    }
  }
}

/**
 * Bind password visibility toggles (eye icons)
 */
function bindPasswordToggles() {
  document.querySelectorAll('.auth-password-toggle').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetInputId = btn.getAttribute('data-target');
      const input = document.getElementById(targetInputId);
      if (!input) return;

      const isPassword = input.type === 'password';
      input.type = isPassword ? 'text' : 'password';

      // Update eye icon SVG
      btn.innerHTML = isPassword ? `
        <!-- Eye Open (Visible) -->
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
          <circle cx="12" cy="12" r="3"></circle>
        </svg>
      ` : `
        <!-- Eye with Slash (Hidden) -->
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
          <line x1="1" y1="1" x2="23" y2="23"></line>
        </svg>
      `;
    });
  });
}

/**
 * Bind Auth Form Submissions and Navigation Links
 */
function bindAuthEvents() {
  // Brand logo click -> return to landing
  document.querySelectorAll('.auth-brand-link').forEach(brand => {
    brand.addEventListener('click', (e) => {
      e.preventDefault();
      returnToLanding();
    });
  });

  // Switch to Signup link
  const linkToSignup = document.getElementById('auth-link-to-signup');
  if (linkToSignup) {
    linkToSignup.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToAuth('signup');
    });
  }

  // Switch to Login link from Signup
  const linkToLogin = document.getElementById('auth-link-to-login');
  if (linkToLogin) {
    linkToLogin.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToAuth('login');
    });
  }

  // Forgot password link from Login
  const linkToForgot = document.getElementById('auth-link-forgot-password');
  if (linkToForgot) {
    linkToForgot.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToAuth('forgot-password');
    });
  }

  // Back to login link from Forgot Password
  const linkForgotToLogin = document.getElementById('auth-link-forgot-to-login');
  if (linkForgotToLogin) {
    linkForgotToLogin.addEventListener('click', (e) => {
      e.preventDefault();
      navigateToAuth('login');
    });
  }

  // Login Form Submission
  const loginForm = document.getElementById('auth-login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLoginSubmit);
  }

  // Signup Form Submission
  const signupForm = document.getElementById('auth-signup-form');
  if (signupForm) {
    signupForm.addEventListener('submit', handleSignupSubmit);
  }

  // Forgot Password Form Submission
  const forgotForm = document.getElementById('auth-forgot-form');
  if (forgotForm) {
    forgotForm.addEventListener('submit', handleForgotSubmit);
  }
}

/**
 * Email validation helper (standard regex)
 */
function isValidEmail(email) {
  const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return re.test(String(email).toLowerCase());
}

/**
 * Set field error state
 */
function setFieldError(fieldId, errorMessage) {
  const group = document.getElementById(`${fieldId}-group`);
  const errorEl = document.getElementById(`${fieldId}-error`);
  if (group) group.classList.add('has-error');
  if (errorEl) errorEl.textContent = errorMessage;
}

/**
 * Clear field error state
 */
function clearFieldError(fieldId) {
  const group = document.getElementById(`${fieldId}-group`);
  if (group) group.classList.remove('has-error');
}

/**
 * Clear all auth error states and alert banners
 */
function clearAuthErrors() {
  document.querySelectorAll('.auth-form-group').forEach(el => el.classList.remove('has-error'));
  document.querySelectorAll('.auth-banner-alert').forEach(el => {
    el.style.display = 'none';
    el.textContent = '';
  });
}

/**
 * Handle Login Form Submit
 */
function handleLoginSubmit(e) {
  e.preventDefault();
  clearAuthErrors();

  const emailInput = document.getElementById('login-email');
  const passwordInput = document.getElementById('login-password');
  const submitBtn = document.getElementById('btn-login-submit');

  const email = emailInput ? emailInput.value.trim() : '';
  const password = passwordInput ? passwordInput.value : '';

  let hasError = false;

  if (!email) {
    setFieldError('login-email', 'Please enter your email');
    hasError = true;
  } else if (!isValidEmail(email)) {
    setFieldError('login-email', 'Please enter a valid email address');
    hasError = true;
  }

  if (!password) {
    setFieldError('login-password', 'Please enter your password');
    hasError = true;
  }

  if (hasError) return;

  // Set loading state
  if (submitBtn) {
    submitBtn.classList.add('is-loading');
    submitBtn.disabled = true;
    const labelSpan = submitBtn.querySelector('.auth-btn-label');
    if (labelSpan) labelSpan.textContent = 'Logging in...';
  }

  // Simulate authentication latency & login
  setTimeout(() => {
    if (submitBtn) {
      submitBtn.classList.remove('is-loading');
      submitBtn.disabled = false;
      const labelSpan = submitBtn.querySelector('.auth-btn-label');
      if (labelSpan) labelSpan.textContent = 'Login';
    }

    // Save session in localStorage
    try {
      localStorage.setItem('netgravity_user', JSON.stringify({
        email: email,
        name: email.split('@')[0],
        company: 'Kearney Logistics',
        loggedInAt: new Date().toISOString()
      }));
    } catch (e) {}

    // Transition to main dashboard
    const authPage = document.getElementById('auth-page');
    if (authPage) {
      authPage.classList.add('hidden');
      authPage.style.display = 'none';
    }

    if (typeof window.enterApp === 'function') {
      window.enterApp('home');
    }
  }, 450);
}

/**
 * Handle Create Account Form Submit
 */
function handleSignupSubmit(e) {
  e.preventDefault();
  clearAuthErrors();

  const nameInput = document.getElementById('signup-name');
  const emailInput = document.getElementById('signup-email');
  const passwordInput = document.getElementById('signup-password');
  const confirmPasswordInput = document.getElementById('signup-confirm-password');
  const companyInput = document.getElementById('signup-company');
  const termsCheckbox = document.getElementById('signup-terms');
  const submitBtn = document.getElementById('btn-signup-submit');

  const name = nameInput ? nameInput.value.trim() : '';
  const email = emailInput ? emailInput.value.trim() : '';
  const password = passwordInput ? passwordInput.value : '';
  const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : '';
  const company = companyInput ? companyInput.value.trim() : '';
  const termsChecked = termsCheckbox ? termsCheckbox.checked : false;

  let hasError = false;

  if (!name) {
    setFieldError('signup-name', 'Please enter your full name');
    hasError = true;
  }

  if (!email) {
    setFieldError('signup-email', 'Please enter your work email');
    hasError = true;
  } else if (!isValidEmail(email)) {
    setFieldError('signup-email', 'Please enter a valid work email address');
    hasError = true;
  }

  if (!password) {
    setFieldError('signup-password', 'Please create a password');
    hasError = true;
  } else if (password.length < 6) {
    setFieldError('signup-password', 'Password must be at least 6 characters');
    hasError = true;
  }

  if (!confirmPassword) {
    setFieldError('signup-confirm-password', 'Please confirm your password');
    hasError = true;
  } else if (password !== confirmPassword) {
    setFieldError('signup-confirm-password', 'Passwords do not match');
    hasError = true;
  }

  if (!company) {
    setFieldError('signup-company', 'Please enter your company name');
    hasError = true;
  }

  if (!termsChecked) {
    setFieldError('signup-terms', 'You must agree to the Terms of Service and Privacy Policy');
    hasError = true;
  }

  if (hasError) return;

  // Set loading state
  if (submitBtn) {
    submitBtn.classList.add('is-loading');
    submitBtn.disabled = true;
    const labelSpan = submitBtn.querySelector('.auth-btn-label');
    if (labelSpan) labelSpan.textContent = 'Creating Account...';
  }

  // Simulate account creation
  setTimeout(() => {
    if (submitBtn) {
      submitBtn.classList.remove('is-loading');
      submitBtn.disabled = false;
      const labelSpan = submitBtn.querySelector('.auth-btn-label');
      if (labelSpan) labelSpan.textContent = 'Create Account';
    }

    // Save session in localStorage
    try {
      localStorage.setItem('netgravity_user', JSON.stringify({
        email: email,
        name: name,
        company: company,
        loggedInAt: new Date().toISOString()
      }));
    } catch (e) {}

    // Transition to main dashboard
    const authPage = document.getElementById('auth-page');
    if (authPage) {
      authPage.classList.add('hidden');
      authPage.style.display = 'none';
    }

    if (typeof window.enterApp === 'function') {
      window.enterApp('home');
    }
  }, 500);
}

/**
 * Handle Forgot Password Submit
 */
function handleForgotSubmit(e) {
  e.preventDefault();
  clearAuthErrors();

  const emailInput = document.getElementById('forgot-email');
  const submitBtn = document.getElementById('btn-forgot-submit');
  const alertSuccess = document.getElementById('forgot-alert-success');

  const email = emailInput ? emailInput.value.trim() : '';

  if (!email) {
    setFieldError('forgot-email', 'Please enter your work email');
    return;
  } else if (!isValidEmail(email)) {
    setFieldError('forgot-email', 'Please enter a valid work email address');
    return;
  }

  // Set loading state
  if (submitBtn) {
    submitBtn.classList.add('is-loading');
    submitBtn.disabled = true;
    const labelSpan = submitBtn.querySelector('.auth-btn-label');
    if (labelSpan) labelSpan.textContent = 'Sending Reset Link...';
  }

  setTimeout(() => {
    if (submitBtn) {
      submitBtn.classList.remove('is-loading');
      submitBtn.disabled = false;
      const labelSpan = submitBtn.querySelector('.auth-btn-label');
      if (labelSpan) labelSpan.textContent = 'Send Reset Link';
    }

    if (alertSuccess) {
      alertSuccess.style.display = 'flex';
      alertSuccess.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <span>Reset instructions sent to <strong>${email}</strong>. Please check your inbox.</span>
      `;
    }
  }, 450);
}

// Expose globally on window for inline clicks
if (typeof window !== 'undefined') {
  window.navigateToAuth = navigateToAuth;
  window.returnToLanding = returnToLanding;
}
