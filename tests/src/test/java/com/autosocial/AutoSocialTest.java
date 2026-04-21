package com.autosocial;

import org.junit.jupiter.api.Test;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

public class AutoSocialTest extends BaseTest {

    @Test
    public void testHomepageLoads() {
        driver.get(BASE_URL);
        assertTrue(driver.getTitle().contains("AutoSocial AI"));
    }

    @Test
    public void testFolderMonitoring() {
        driver.get(BASE_URL + "/monitor");
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        
        WebElement folderInput = wait.until(
            ExpectedConditions.presenceOfElementLocated(By.id("folder-path"))
        );
        folderInput.sendKeys("D:/test-folder");
        
        driver.findElement(By.id("start-monitoring")).click();
        
        WebElement status = wait.until(
            ExpectedConditions.presenceOfElementLocated(By.id("monitoring-status"))
        );
        assertTrue(status.getText().contains("Monitoring active"));
    }

    @Test
    public void testContentGeneration() {
        driver.get(BASE_URL + "/generate");
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(20));
        
        driver.findElement(By.id("generate-content")).click();
        
        WebElement content = wait.until(
            ExpectedConditions.presenceOfElementLocated(By.className("generated-content"))
        );
        assertNotEquals("", content.getText());
    }

    @Test
    public void testPostScheduling() {
        driver.get(BASE_URL + "/schedule");
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        
        WebElement dateInput = driver.findElement(By.id("schedule-date"));
        dateInput.sendKeys("2024-12-31");
        
        driver.findElement(By.id("schedule-post")).click();
        
        WebElement confirmation = wait.until(
            ExpectedConditions.presenceOfElementLocated(By.className("schedule-confirmation"))
        );
        assertTrue(confirmation.getText().contains("Post scheduled"));
    }

    @Test
    public void testApiConfiguration() {
        driver.get(BASE_URL + "/settings");
        WebDriverWait wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        
        WebElement apiKey = driver.findElement(By.id("openai-key"));
        apiKey.sendKeys("test-key");
        
        driver.findElement(By.id("save-settings")).click();
        
        WebElement message = wait.until(
            ExpectedConditions.presenceOfElementLocated(By.className("settings-saved"))
        );
        assertTrue(message.getText().contains("Settings saved"));
    }
}
