# Canvas LTI Technical Reference

## Purpose

This document serves as a comprehensive technical reference for implementing Canvas LTI tools that feel native and avoid common integration pitfalls. It complements the PRD and Frontend Specification with detailed implementation guidance, code patterns, and real-world examples.

**Target Audience:** Architect and Developer agents building the QA Automation LTI Tool

---

## Canvas LTI Iframe Limitations & Solutions

### Critical Iframe Limitations

#### 1. Session & Cookie Management

**Issue:** Canvas iframes block cross-site cookies by default  
**Solution:** Configure SESSION_COOKIE_SAMESITE = 'None' and SESSION_COOKIE_SECURE = True  
**Implementation Status:** Should be implemented in FastAPI settings

```python
# Required configuration for Canvas iframe compatibility
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
```

#### 2. Security Headers

**Issue:** Default X-Frame-Options blocks iframe embedding  
**Solution:** Set X_FRAME_OPTIONS = 'ALLOWALL'  
**Risk:** Carefully validate trusted origins in CSRF_TRUSTED_ORIGINS

```python
# Security header configuration
X_FRAME_OPTIONS = 'ALLOWALL'
# Ensure CSRF protection is properly configured
CSRF_TRUSTED_ORIGINS = ['https://canvas.domain.edu', 'https://your-lti-domain.com']
```

#### 3. HTTPS Requirements

**Issue:** Mixed content errors in iframes  
**Solution:** All LTI endpoints must use HTTPS  
**Implementation:** Railway SSL properly configured for production

### Best Practices from LTI Specialists

#### 4. State Management

**Critical Pattern:** Store LTI context in session immediately after launch

```python
def lti_launch(request):
    # Store all LTI claims for later use
    request.session['lti_user_id'] = launch_data.get('sub')
    request.session['lti_context_id'] = launch_data.get_context_id()
    request.session['canvas_course_id'] = launch_data.get_custom_claim('course_id')
    request.session['canvas_api_token'] = launch_data.get_custom_claim('api_token')  # If available
    request.session['lti_target_link_uri_base'] = launch_data.get_target_link_uri_base()
```

#### 5. Error Handling for iframe Context

**Issue:** Limited debugging in iframes  
**Solution:** Comprehensive logging + user-friendly error pages that work within iframe constraints

**Implementation Strategy:**
- Comprehensive logging (as implemented in LOGGING config)
- User-friendly error pages that work within iframe constraints
- Avoid pop-ups or external redirects

#### 6. Canvas API Integration

**Pattern:** Use stored LTI context for API calls

```python
# Use stored LTI context for API calls
def get_canvas_client(request):
    canvas_url = request.session.get('lti_target_link_uri_base')
    token = request.session.get('canvas_api_token')  # From LTI claims
    return Canvas(canvas_url, token)
```

#### 7. UI/UX Considerations for iframe Context

**Constraint:** Limited screen real estate  
**Solution:** Progressive disclosure, collapsible sections  
**Avoid:** Pop-ups, new windows (blocked in some Canvas configurations)  
**Use:** Modal overlays within the iframe

#### 8. Deep Linking Configuration

**Essential for Content Creation:**

```python
# Enable content creation from within LTI
LTI_CONFIG = {
    "target_link_uri": "https://your-app.com/lti/launch",
    "oidc_login_uri": "https://your-app.com/lti/login",
    "deep_linking": {
        "deep_linking_uri": "https://your-app.com/lti/deep-linking"
    }
}
```

### Performance Optimizations

#### 9. Minimize Initial Load

**Strategies:**
- Use lazy loading for non-critical components
- Implement skeleton screens for Canvas API calls
- Cache Canvas data with appropriate TTL

#### 10. Handle Canvas Timeouts

**Problem:** Canvas may timeout iframe content  
**Solution:** Keep-alive mechanism

```python
# Canvas may timeout iframe content
def keep_alive_endpoint(request):
    """Endpoint to prevent Canvas iframe timeouts"""
    return JsonResponse({"status": "alive"})

# Frontend: Periodic ping to keep session active
# setInterval(() => fetch('/keep-alive'), 300000); // 5 minutes
```

---

## Canvas Native LTI Examples Analysis

### Successful Canvas LTI Integrations

These examples demonstrate how to achieve seamless Canvas integration:

#### Ally by Blackboard
- **Visual Integration:** Seamlessly appears as course accessibility indicators
- **Functional Integration:** Integrates directly into Canvas content areas without feeling separate
- **Design Approach:** Uses Canvas color scheme and typography
- **UX Pattern:** Provides contextual overlays rather than taking users away

#### Turnitin
- **Visual Integration:** Assignment submission flow feels like native Canvas
- **Functional Integration:** Grade passback appears in Canvas gradebook naturally
- **Design Approach:** Similarity report opens in Canvas-styled modal
- **UX Pattern:** Uses Canvas's existing UI patterns for file uploads

#### Kaltura (Canvas Video)
- **Visual Integration:** Video player matches Canvas media styling
- **Functional Integration:** Recording tools appear as native Canvas buttons
- **Design Approach:** Content library integrates into Canvas file system
- **UX Pattern:** Uses Canvas's existing content editor patterns

#### VitalSource (Bookshelf)
- **Visual Integration:** Reading interface matches Canvas theme
- **Functional Integration:** Highlights sync with Canvas annotations
- **Design Approach:** Navigation breadcrumbs follow Canvas patterns
- **UX Pattern:** Progress tracking appears in Canvas course progress

### Key Design Patterns They Use

#### Visual Integration
- **Canvas Color Palette:** (#394B58, #008EE2, etc.)
- **Canvas Typography:** (LatoWeb, source-sans-pro)
- **Canvas Spacing:** Canvas grid system
- **Canvas Controls:** Button and form styling

#### Functional Integration
- **Deep Linking:** To specific course content
- **Grade Passback:** With Canvas gradebook
- **Notifications:** Canvas notification system integration
- **Navigation:** Course navigation integration

#### UX Patterns
- **Contextual Help:** Using Canvas help system style
- **Error Messages:** Matching Canvas error patterns
- **Loading States:** Consistent with Canvas
- **Modal Overlays:** Using Canvas modal styling

### What Makes Them Feel Native

1. **No Visual Jarring:** Seamless color/font transitions
2. **Familiar Interactions:** Buttons, forms work like Canvas
3. **Contextual Placement:** Appear where users expect them
4. **Consistent Navigation:** Breadcrumbs and back buttons work naturally
5. **Canvas Data Integration:** Use Canvas roster, gradebook, etc.

---

## Implementation Guidelines for QA Automation LTI

### Priority Implementation Checklist

**High Priority - iframe Compatibility:**
- [ ] Configure session cookies for iframe context
- [ ] Set appropriate security headers
- [ ] Implement keep-alive mechanism
- [ ] Design for limited screen real estate
- [ ] Test within actual Canvas iframe

**High Priority - Canvas Integration:**
- [ ] Store LTI context in session immediately
- [ ] Use Canvas color palette and typography
- [ ] Follow Canvas form and button patterns
- [ ] Implement Canvas-style loading states
- [ ] Handle Canvas API authentication via LTI context

**Medium Priority - UX Native Feel:**
- [ ] Progressive disclosure for complex features
- [ ] Canvas-style breadcrumb navigation
- [ ] Modal overlays instead of pop-ups
- [ ] Canvas error message patterns
- [ ] Consistent with Canvas help system

**Low Priority - Advanced Integration:**
- [ ] Deep linking configuration for future features
- [ ] Grade passback capability architecture
- [ ] Canvas notification system integration

### Canvas API Best Practices for LTI Context

#### Authentication Pattern
```python
# Get Canvas API access using LTI launch context
def get_canvas_api_access(lti_launch_data):
    # Extract Canvas instance URL from LTI claims
    canvas_url = lti_launch_data.get('target_link_uri_base')
    
    # Get user's API token (if available via custom claims)
    api_token = lti_launch_data.get_custom_claim('api_token')
    
    # Alternative: Use LTI user context for API calls
    user_id = lti_launch_data.get('sub')
    course_id = lti_launch_data.get_custom_claim('course_id')
    
    return canvas_url, api_token, user_id, course_id
```

#### Rate Limiting Handling
```python
import time
import random

def canvas_api_call_with_backoff(api_function, *args, **kwargs):
    """Handle Canvas API rate limiting with exponential backoff"""
    max_retries = 5
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            return api_function(*args, **kwargs)
        except RateLimitException as e:
            if attempt == max_retries - 1:
                raise
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
    
    raise Exception("Max retries exceeded for Canvas API call")
```

---

## Testing Strategy for Canvas LTI Integration

### iframe Compatibility Testing
1. **Browser Testing:** Test in Canvas iframe across Chrome, Firefox, Safari
2. **Device Testing:** Desktop and tablet viewports within Canvas
3. **Session Management:** Verify session persistence during long operations
4. **Error Scenarios:** Test error handling within iframe constraints

### Canvas Integration Testing
1. **LTI Launch Flow:** Test with actual Canvas development instance
2. **API Integration:** Verify Canvas API calls work with LTI context
3. **Visual Integration:** Compare with native Canvas interfaces
4. **Performance:** Test QA operations with various course sizes

### User Experience Testing
1. **Learning Designer Testing:** Non-technical users complete QA tasks
2. **Navigation Testing:** Verify breadcrumbs and back buttons work
3. **Error Recovery:** Test graceful handling of Canvas API failures
4. **Mobile Responsiveness:** Test within Canvas mobile app if applicable

---

## Reference Links and Resources

### Canvas LTI Documentation
- [Canvas LTI 1.3 Guide](https://canvas.instructure.com/doc/api/file.lti_dev_key_config.html)
- [Canvas API Documentation](https://canvas.instructure.com/doc/api/)

### Successful LTI Examples
- [Ally by Blackboard](https://www.blackboard.com/teaching-learning/accessibility/ally) - Accessibility integration
- [Turnitin](https://www.turnitin.com/products/originality-check) - Assignment submission integration
- [Kaltura](https://corp.kaltura.com/solutions/education/) - Video content integration
- [VitalSource](https://www.vitalsource.com/) - Digital textbook integration

### Technical Implementation Resources
- [PyLTI1p3 Library](https://github.com/dmitry-viskov/pylti1.3) - LTI 1.3 implementation for Python
- [Canvas Color Palette](https://design.instructure.com/color/) - Official Canvas design system
- [Canvas Typography](https://design.instructure.com/typography/) - Canvas font system

---

## Document Maintenance

**Last Updated:** [Current Date]  
**Next Review:** After MVP implementation  
**Maintained By:** Technical team implementing QA Automation LTI Tool

**Change Log:**
| Date | Change | Author |
|------|--------|--------|
| [Current Date] | Initial technical reference creation | UX Expert | 