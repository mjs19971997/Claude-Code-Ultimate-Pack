# Spring Security

Configuring Spring Security 7 (Spring Boot 4.1.x) for APIs and web apps: `SecurityFilterChain`, multiple chains, method security, JWT resource server, CSRF and CORS rules, password encoding and Actuator protection. OAuth 2.0 and OIDC protocol design, token lifetimes and identity provider choice belong to authentication-expert; this file covers the Spring side.

## Contents

1. [Dependencies](#1-dependencies)
2. [Filter chain basics](#2-filter-chain-basics)
3. [Multiple chains](#3-multiple-chains)
4. [Method security](#4-method-security)
5. [JWT resource server](#5-jwt-resource-server)
6. [CSRF and CORS](#6-csrf-and-cors)
7. [Passwords and user stores](#7-passwords-and-user-stores)
8. [Migrating from Security 6](#8-migrating-from-security-6)
9. [Testing security](#9-testing-security)

## 1. Dependencies

- `spring-boot-starter-security` for the core; `spring-boot-starter-security-oauth2-resource-server` for JWT or opaque-token APIs (the OAuth2 starters gained the `security-` prefix in Boot 4); `spring-boot-starter-security-test` for `@WithMockUser` and the MockMvc helpers.
- With the starter on the classpath and no configuration, every endpoint requires authentication and a generated password is logged at startup. Define your own `SecurityFilterChain` before the first deployment.
- Spring Authorization Server ships with Spring Security in version 7; its version follows `spring-security.version`.

## 2. Filter chain basics

Only the lambda DSL exists in Security 7. Each `HttpSecurity` call takes a `Customizer`; there is no `and()`.

```java
@Configuration
@EnableWebSecurity
class WebSecurityConfig {

    @Bean
    SecurityFilterChain web(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/", "/assets/**", "/login").permitAll()
                .requestMatchers("/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())
            .formLogin(Customizer.withDefaults())
            .logout(Customizer.withDefaults())
            .headers(h -> h.contentSecurityPolicy(csp ->
                csp.policyDirectives("default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'")));
        return http.build();
    }
}
```

- Rules are evaluated in order; the first match wins, so put specific rules before general ones and finish with `anyRequest().authenticated()` (or `denyAll()` for a default-deny posture).
- `requestMatchers(String...)` uses path patterns; use `PathPatternRequestMatcher.withDefaults().matcher(HttpMethod.POST, "/api/**")` (replacing `AntPathRequestMatcher` and `MvcRequestMatcher`, which Security 7 removed) when a method or custom base path is needed.
- Use `authorizeHttpRequests`; `authorizeRequests` was removed in 7.
- Do not add `unsafe-inline` or `unsafe-eval` to the CSP; use nonces or hashes for inline scripts, or move scripts to files.
- Default headers (`X-Content-Type-Options`, cache control, frame options) are on; leave them on.
- Session fixation protection is on by default; for stateless APIs set `SessionCreationPolicy.STATELESS`.

## 3. Multiple chains

Use `securityMatcher` and `@Order` when API, UI and management endpoints need different rules. The first chain whose matcher matches handles the request.

```java
@Bean
@Order(1)
SecurityFilterChain actuator(HttpSecurity http) throws Exception {
    http.securityMatcher("/actuator/**")
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/actuator/health/**").permitAll()
            .anyRequest().hasRole("OPS"))
        .httpBasic(Customizer.withDefaults());
    return http.build();
}

@Bean
@Order(2)
SecurityFilterChain api(HttpSecurity http) throws Exception {
    http.securityMatcher("/api/**")
        .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
        .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()))
        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .csrf(csrf -> csrf.disable());   // bearer tokens only, no cookie authentication
    return http.build();
}
```

- If `management.endpoints.web.base-path` is changed, update the Actuator matcher to match (or use Boot's `EndpointRequest` matcher; check its package in the current docs).
- A request that matches no chain's matcher gets no protection from these chains; add a last catch-all chain with `anyRequest().denyAll()` or `authenticated()`.
- Basic auth over plain HTTP exposes credentials; terminate TLS in front and set `server.forward-headers-strategy` correctly (details: nginx-expert for the proxy side).

## 4. Method security

- Enable with `@EnableMethodSecurity` on a configuration class (pre/post annotations are on by default).
- Put authorization on service methods so every entry point (HTTP, messaging, scheduled jobs) is covered.

```java
@PreAuthorize("hasAuthority('SCOPE_notes:write')")
public void rename(Long id, String ownerId, String title) { /* ... */ }

@PreAuthorize("hasRole('ADMIN') or #ownerId == authentication.name")
public List<NoteSummary> list(String ownerId) { /* ... */ }

@PostAuthorize("returnObject.ownerId == authentication.name")
public Note load(Long id) { /* ... */ }
```

- `@PreAuthorize` is a coarse check; it does not replace the owner condition in the data query (see spring-data-jpa.md section 7). `@PostAuthorize` runs after the data was loaded and after side effects of the method, so do not use it on methods that write.
- Role names: `hasRole('ADMIN')` checks the authority `ROLE_ADMIN`; `hasAuthority('SCOPE_x')` checks the literal string. JWT scopes become `SCOPE_` authorities by default.
- Annotations on a bean method work through a proxy: self-invocation bypasses them, like `@Transactional`.

## 5. JWT resource server

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: ${JWT_ISSUER_URI}      # discovery of keys and issuer validation
```

- With `issuer-uri`, Boot configures a `JwtDecoder` that validates signature, expiry and issuer. If the provider does not support discovery, set `jwk-set-uri` and add an issuer validator yourself.
- Validate the audience: add an `OAuth2TokenValidator<Jwt>` for `aud` to a custom `JwtDecoder` bean, otherwise any token from the same issuer is accepted by every API.
- Map claims to authorities with a `JwtAuthenticationConverter` bean when roles come from a custom claim instead of `scope`:

```java
@Bean
JwtAuthenticationConverter jwtAuthenticationConverter() {
    var authorities = new JwtGrantedAuthoritiesConverter();
    authorities.setAuthoritiesClaimName("roles");
    authorities.setAuthorityPrefix("ROLE_");
    var converter = new JwtAuthenticationConverter();
    converter.setJwtGrantedAuthoritiesConverter(authorities);
    return converter;
}
```

- Use `oauth2ResourceServer(o -> o.jwt(j -> j.jwtAuthenticationConverter(converter)))` to apply it. For opaque tokens use `.opaqueToken(...)` with an introspection endpoint.
- Take the user identity for owner filters from `jwt.getSubject()`; never trust an `ownerId` supplied by the client.
- Never log tokens. Never put a signing secret in `application.yml`; asymmetric keys from the issuer avoid sharing any secret with the API.

## 6. CSRF and CORS

- CSRF protects requests that the browser authenticates automatically (session cookies, HTTP Basic, client certificates). Keep it enabled for server-rendered apps and for SPAs that use cookie sessions.
- Disable CSRF only for chains that authenticate exclusively through an `Authorization` header and keep no session; note the reason in a comment.
- SPAs with cookie sessions: `CookieCsrfTokenRepository.withHttpOnlyFalse()` lets JavaScript read the token cookie and send it back in the `X-XSRF-TOKEN` header. Check the current reference for the request-handler setup used with single-page apps.
- Do not exempt individual endpoints from CSRF for convenience; exempt a whole stateless chain, with a reason, or nothing.
- CORS: define a `CorsConfigurationSource` bean with explicit origins and methods and enable it with `.cors(Customizer.withDefaults())`. `allowedOrigins("*")` together with `allowCredentials(true)` is rejected by the framework and is unsafe in intent; list the real origins.
- CORS is a browser rule, not authentication: the API still needs authorization on every request.

## 7. Passwords and user stores

```java
@Bean
PasswordEncoder passwordEncoder() {
    return PasswordEncoderFactories.createDelegatingPasswordEncoder();   // {bcrypt}... prefix, upgradeable
}
```

- `DelegatingPasswordEncoder` stores the algorithm id with the hash (`{bcrypt}`, `{argon2@SpringSecurity_v5_8}`), so you can change the default later and re-encode on login (`UserDetailsPasswordService`).
- `BCryptPasswordEncoder` is the long-standing choice; `Argon2PasswordEncoder.defaultsForSpringSecurity_v5_8()` is available when the BouncyCastle dependency is present. `Pbkdf2PasswordEncoder` and `SCryptPasswordEncoder` also exist. Do not use `NoOpPasswordEncoder`, MD5 or plain SHA.
- Passwords come from the user at runtime, from a hash column in the database, or from a secret manager; do not define `UserDetails` with real passwords in code or `spring.security.user.password` outside local experiments.
- Rate-limit login attempts and use generic error messages; lockout and MFA design belongs to authentication-expert.

## 8. Migrating from Security 6

| Security 6 code | Security 7 |
|---|---|
| `http.csrf().disable().and()...` | `http.csrf(csrf -> csrf.disable())` |
| `.authorizeRequests()` | `.authorizeHttpRequests(...)` |
| `AntPathRequestMatcher`, `MvcRequestMatcher` | `PathPatternRequestMatcher` |
| `http.apply(customDsl)` | `http.with(customDsl, Customizer.withDefaults())` |
| `AuthorizationManager#check` | `AuthorizationManager#authorize` |
| OAuth2 password grant | removed; use authorization code with PKCE or client credentials |

Move to the latest 6.5.x first and fix deprecation warnings; 6.5 adds preparation hooks for 7.0. Read the 7.0 migration guide for SAML and LDAP removals.

## 9. Testing security

- Add `spring-boot-starter-security-test`. For `@WebMvcTest`, import your security configuration (`@Import(SecurityConfig.class)`) so tests exercise the real rules.
- Use `SecurityMockMvcRequestPostProcessors.jwt()` for resource-server tests and `.with(csrf())` for cookie-session POSTs; `@WithMockUser(roles = "ADMIN")` for role checks.
- Assert 401 without credentials, 403 with the wrong role, and 404 for another user's resource.

```java
mockMvc.perform(delete("/api/notes/{id}", 1)
        .with(jwt().jwt(j -> j.subject("bob"))))
    .andExpect(status().isNotFound());       // note 1 belongs to alice
```
